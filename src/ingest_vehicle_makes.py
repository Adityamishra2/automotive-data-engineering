
import json
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from src.data_quality import validate_vehicle_makes
import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

db_url = URL.create(
    "postgresql+psycopg",
    username=os.environ["PGUSER"],
    password=os.environ["PGPASSWORD"],
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    database=os.environ["PGDATABASE"],
)

engine = create_engine(db_url, pool_pre_ping=True)

PIPELINE_NAME = "automotive_vehicle_makes"
API_URL = (
    "https://vpic.nhtsa.dot.gov/api/vehicles/"
    "GetAllMakes?format=json"
)

CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS public.etl_run_log (
        run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        pipeline_name VARCHAR(100) NOT NULL,
        status VARCHAR(20) NOT NULL
            CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
        start_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMPTZ,
        source_rows INTEGER DEFAULT 0,
        valid_rows INTEGER DEFAULT 0,
        invalid_rows INTEGER DEFAULT 0,
        duplicate_rows INTEGER DEFAULT 0,
        inserted_rows INTEGER DEFAULT 0,
        updated_rows INTEGER DEFAULT 0,
        unchanged_rows INTEGER DEFAULT 0,
        error_message TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS public.raw_vehicle_makes (
        make_id BIGINT PRIMARY KEY,
        make_name TEXT NOT NULL,
        first_loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]

INSERT_RUN = text("""
    INSERT INTO public.etl_run_log (pipeline_name, status)
    VALUES (:name, 'RUNNING')
    RETURNING run_id
""")

FINISH_RUN = text("""
    UPDATE public.etl_run_log
    SET status = :status,
        end_time = CURRENT_TIMESTAMP,
        source_rows = :source_rows,
        valid_rows = :valid_rows,
        invalid_rows = :invalid_rows,
        duplicate_rows = :duplicate_rows,
        inserted_rows = :inserted_rows,
        updated_rows = :updated_rows,
        unchanged_rows = :unchanged_rows,
        error_message = :error_message
    WHERE run_id = :run_id
""")

SELECT_EXISTING = text("""
    SELECT make_id, make_name
    FROM public.raw_vehicle_makes
""")

INSERT_MAKE = text("""
    INSERT INTO public.raw_vehicle_makes (make_id, make_name)
    VALUES (:make_id, :make_name)
""")

UPDATE_MAKE = text("""
    UPDATE public.raw_vehicle_makes
    SET make_name = :make_name,
        updated_at = CURRENT_TIMESTAMP
    WHERE make_id = :make_id
""")


def main():
    run_id = None
    counts = {
        "source_rows": 0,
        "valid_rows": 0,
        "invalid_rows": 0,
        "duplicate_rows": 0,
        "inserted_rows": 0,
        "updated_rows": 0,
        "unchanged_rows": 0,
    }

    # Create tables and register the run.
    with engine.begin() as conn:
        for ddl in CREATE_TABLES:
            conn.execute(text(ddl))

        run_id = conn.execute(
            INSERT_RUN, {"name": PIPELINE_NAME}
        ).scalar_one()

    print(f"Started pipeline run_id={run_id}")

    try:
        # Extract.
        response = requests.get(API_URL, timeout=60)
        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload.get("Results"), list):
            raise ValueError("Unexpected API response structure")

        df = pd.DataFrame(payload["Results"])
        counts["source_rows"] = len(df)

        required = {"Make_ID", "Make_Name"}
        if not required.issubset(df.columns):
            raise ValueError("Required API columns are missing")

        # Preserve the raw source response.
        run_label = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        raw_file = RAW_DIR / f"vehicle_makes_{run_label}.json"
        raw_file.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )


       
        # Transform and validate using the tested function.
        df = df.rename(
            columns={
                "Make_ID": "make_id",
                "Make_Name": "make_name",
            }
        )[["make_id", "make_name"]]

        df, quality_metrics = validate_vehicle_makes(df)

        counts.update(quality_metrics)

        if df.empty:
            raise ValueError("No valid vehicle makes found")

        parquet_file = (
            PROCESSED_DIR / f"vehicle_makes_{run_label}.parquet"
        )
        df.to_parquet(parquet_file, index=False)

        # Compare and load atomically.
        with engine.begin() as conn:
            existing_rows = conn.execute(
                SELECT_EXISTING
            ).mappings().all()

            existing = {
                int(row["make_id"]): row["make_name"]
                for row in existing_rows
            }

            for row in df.to_dict(orient="records"):
                make_id = row["make_id"]
                make_name = row["make_name"]

                if make_id not in existing:
                    conn.execute(
                        INSERT_MAKE,
                        {
                            "make_id": make_id,
                            "make_name": make_name,
                        },
                    )
                    counts["inserted_rows"] += 1

                elif existing[make_id] != make_name:
                    conn.execute(
                        UPDATE_MAKE,
                        {
                            "make_id": make_id,
                            "make_name": make_name,
                        },
                    )
                    counts["updated_rows"] += 1

                else:
                    counts["unchanged_rows"] += 1

            conn.execute(
                FINISH_RUN,
                {
                    "run_id": run_id,
                    "status": "SUCCESS",
                    **counts,
                    "error_message": None,
                },
            )

        print("\nPipeline completed successfully")
        for key, value in counts.items():
            print(f"{key}: {value}")

    except Exception as exc:
        print(f"Pipeline failed: {type(exc).__name__}: {exc}")

        try:
            with engine.begin() as conn:
                conn.execute(
                    FINISH_RUN,
                    {
                        "run_id": run_id,
                        "status": "FAILED",
                        **counts,
                        "error_message": str(exc)[:10000],
                    },
                )
        except Exception:
            traceback.print_exc()

        raise

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
