import pandas as pd
from src.data_quality import validate_vehicle_makes

def test_valid_records_pass():
    df = pd.DataFrame({
        "make_id": [1, 2, 3],
        "make_name": ["Toyota", "Honda", "Ford"],
    })

    clean, metrics = validate_vehicle_makes(df)

    assert len(clean) == 3
    assert metrics["invalid_rows"] == 0
    assert metrics["duplicate_rows"] == 0


def test_missing_ids_are_rejected():
    df = pd.DataFrame({
        "make_id": [1, None],
        "make_name": ["Toyota", "Honda"],
    })

    clean, metrics = validate_vehicle_makes(df)

    assert len(clean) == 1
    assert metrics["invalid_rows"] == 1


def test_blank_names_are_rejected():
    df = pd.DataFrame({
        "make_id": [1, 2],
        "make_name": ["Toyota", "   "],
    })

    clean, metrics = validate_vehicle_makes(df)

    assert clean["make_name"].tolist() == ["Toyota"]
    assert metrics["invalid_rows"] == 1


def test_duplicate_ids_are_removed():
    df = pd.DataFrame({
        "make_id": [1, 1, 2],
        "make_name": ["Toyota", "Toyota Updated", "Honda"],
    })

    clean, metrics = validate_vehicle_makes(df)

    assert clean["make_id"].is_unique
    assert len(clean) == 2
    assert metrics["duplicate_rows"] == 1


def test_missing_columns_raise_error():
    df = pd.DataFrame({
        "make_id": [1, 2],
    })

    try:
        validate_vehicle_makes(df)
    except ValueError as exc:
        assert "Required columns" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
