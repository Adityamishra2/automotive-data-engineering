
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

# Project paths
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

# Database connection
db_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.environ["PGUSER"],
    password=os.environ["PGPASSWORD"],
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    database=os.environ["PGDATABASE"],
)

engine = create_engine(db_url, pool_pre_ping=True)

API_URL = (
    "https://vpic.nhtsa.dot.gov/api/vehicles/"
    "GetAllMakes?format=json"
)


def main():
    run_time = datetime.now(timezone.utc)
    run_id = run_time.strftime("%Y%m%dT%H%M%SZ")

    print("Starting automotive ingestion...")

    # 1. Extract
    response = requests.get(API_URL, timeout=60)
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload.get("Results"), list):
        raise ValueError("Unexpected API response structure")

    # 2. Save raw source data for traceability
    raw_file = RAW_DIR / f"vehicle_makes_{run_id}.json"
    raw_file.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    # 3. Transform and validate
    df = pd.DataFrame(payload["Results"])

    required = {"Make_ID", "Make_Name"}
    if not required.issubset(df.columns):
        raise ValueError("Expected vehicle make columns are missing")

    df = df.rename(
        columns={
            "Make_ID": "make_id",
            "Make_Name": "make_name",
        }
    )[["make_id", "make_name"]]

    source_count = len(df)

    df["make_id"] = pd.to_numeric(
        df["make_id"], errors="coerce"
    )
    df["make_name"] = df["make_name"].astype("string").str.strip()

    invalid_mask = (
        df["make_id"].isna()
        | df["make_name"].isna()
        | df["make_name"].eq("")
    )
    invalid_count = int(invalid_mask.sum())
    df = df.loc[~invalid_mask].copy()

    df["make_id"] = df["make_id"].astype("int64")

    duplicate_count = int(df.duplicated("make_id").sum())
    df = df.drop_duplicates(subset="make_id", keep="last")

    if df.empty:
        raise ValueError("No valid vehicle make records found")

    # 4. Store a processed Parquet snapshot
    parquet_file = (
        PROCESSED_DIR / f"vehicle_makes_{run_id}.parquet"
    )
    df.to_parquet(parquet_file, index=False)

    # 5. Create the destination table
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS raw_vehicle_makes (
            make_id BIGINT PRIMARY KEY,
            make_name TEXT NOT NULL,
            first_loaded_at TIMESTAMPTZ
                NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ
                NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """

    upsert_sql = text("""
        INSERT INTO raw_vehicle_makes (make_id, make_name)
        VALUES (:make_id, :make_name)
        ON CONFLICT (make_id) DO UPDATE
        SET make_name = EXCLUDED.make_name,
            updated_at = CURRENT_TIMESTAMP
        WHERE raw_vehicle_makes.make_name
              IS DISTINCT FROM EXCLUDED.make_name;
    """)

    # 6. Load records using an idempotent upsert
    records = df.to_dict(orient="records")

    with engine.begin() as conn:
        conn.execute(text(create_table_sql))
        conn.execute(upsert_sql, records)

    print("\nPipeline completed successfully")
    print(f"Source rows:       {source_count}")
    print(f"Invalid rows:      {invalid_count}")
    print(f"Duplicate IDs:     {duplicate_count}")
    print(f"Valid unique rows:  {len(df)}")
    print(f"Raw JSON:           {raw_file}")
    print(f"Processed Parquet:  {parquet_file}")
    print("PostgreSQL table:   raw_vehicle_makes")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
