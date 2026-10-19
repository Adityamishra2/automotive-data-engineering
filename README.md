# Automotive Data Engineering Pipeline

A Python-based data ingestion pipeline that extracts vehicle manufacturer data from the NHTSA vPIC API, validates and transforms it using Pandas, stores processed data in Parquet format, and loads it into PostgreSQL.

## Project Architecture

NHTSA vPIC API → Python & Pandas → Data Quality Checks → Parquet → PostgreSQL

## Technologies

- Python
- Pandas
- PostgreSQL
- SQL
- Parquet
- Pytest
- Git and GitHub

## Key Features

- Extracts vehicle manufacturer data from a public API.
- Validates required fields and removes duplicate records.
- Stores raw JSON and processed Parquet files locally.
- Loads data into PostgreSQL using incremental insert/update logic.
- Tracks pipeline execution and data quality metrics.
- Includes automated data quality tests.

## Project Structure

```text
automotive-data-engineering/
├── src/
│   ├── __init__.py
│   ├── data_quality.py
│   └── ingest_vehicle_makes.py
├── tests/
│   └── test_data_quality.py
├── sql/
├── .gitignore
└── README.md
```

## Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install the required Python packages.
4. Configure PostgreSQL credentials in a local `.env` file.
5. Run the pipeline from the project root:

```powershell
python -m src.ingest_vehicle_makes
```

Run the tests:

```powershell
python -m pytest tests/test_data_quality.py -v
```

## Data Source

[NHTSA vPIC API](https://vpic.nhtsa.dot.gov/api/vehicles/GetAllMakes?format=json)

## Future Improvements

- Schedule automated pipeline execution.
- Add more data quality checks.
- Expand the warehouse schema and analytical SQL queries.
- Add pipeline monitoring and reporting.