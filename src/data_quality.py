
import pandas as pd


def validate_vehicle_makes(df):
    """Validate vehicle make records and return cleaned data and metrics."""

    required_columns = {"make_id", "make_name"}

    if not required_columns.issubset(df.columns):
        raise ValueError("Required columns are missing")

    df = df.copy()

    df["make_id"] = pd.to_numeric(
        df["make_id"], errors="coerce"
    )
    df["make_name"] = (
        df["make_name"].astype("string").str.strip()
    )

    invalid_mask = (
        df["make_id"].isna()
        | df["make_name"].isna()
        | df["make_name"].eq("")
    )

    invalid_rows = int(invalid_mask.sum())
    valid_df = df.loc[~invalid_mask].copy()

    valid_df["make_id"] = valid_df["make_id"].astype("int64")

    duplicate_rows = int(
        valid_df.duplicated(subset=["make_id"]).sum()
    )

    clean_df = valid_df.drop_duplicates(
        subset=["make_id"], keep="last"
    )

    metrics = {
        "source_rows": len(df),
        "invalid_rows": invalid_rows,
        "duplicate_rows": duplicate_rows,
        "valid_rows": len(clean_df),
    }

    return clean_df, metrics
