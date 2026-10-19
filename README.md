# Automotive Data Engineering Pipeline

An end-to-end, zero-cost data engineering project that ingests automotive vehicle-make data from a public API, validates and transforms records using Python and Pandas, stores the data in PostgreSQL, and saves analytical snapshots in Parquet format.

## Project Overview

This project demonstrates the fundamentals of building a reliable data ingestion pipeline using free, locally installed tools.

### Architecture

NHTSA vPIC API → Python Ingestion → Data Validation → Raw JSON and Parquet → PostgreSQL

## Technology Stack

- Python
- Pandas
- PostgreSQL
- SQLAlchemy
- Requests
- PyArrow / Parquet
- Git and GitHub

## Features

- Extracts vehicle-make data from a public API.
- Saves raw API responses for traceability.
- Validates required fields and handles invalid records.
- Removes duplicate vehicle-make IDs.
- Saves processed data as Parquet files.
- Loads records into PostgreSQL using an upsert strategy.
- Supports repeatable pipeline execution.

## Project Structure

```text
automotive-data-engineering/
├── data/
│   ├── raw/
│   └── processed/
├── logs/
├── sql/
├── src/
│   └── ingest_vehicle_makes.py
├── .gitignore
├── .env
└── README.md
```

Note: `.env` contains local database credentials and must not be committed to GitHub.

## Prerequisites

- Python installed on Windows
- PostgreSQL installed and running
- Git installed
- Internet access to reach the source API

## Setup

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install pandas requests sqlalchemy "psycopg[binary]" python-dotenv duckdb pyarrow
```

Create a local `.env` file:

```dotenv
PGHOST=localhost
PGPORT=5432
PGDATABASE=automotive_dw
PGUSER=postgres
PGPASSWORD=YOUR_LOCAL_POSTGRES_PASSWORD
```

Create the `automotive_dw` database in PostgreSQL before running the pipeline.

Run the ingestion script:

```powershell
python src/ingest_vehicle_makes.py
```

## Verify the Data

Connect to the `automotive_dw` database in pgAdmin and execute:

```sql
SELECT COUNT(*) AS total_vehicle_makes
FROM public.raw_vehicle_makes;

SELECT *
FROM public.raw_vehicle_makes
ORDER BY make_name
LIMIT 20;
```

## Future Improvements

- ETL run logging and error monitoring
- Incremental ingestion and change detection
- Automated data-quality tests
- Vehicle-model ingestion
- Fact and dimension tables
- Workflow scheduling
- Power BI reporting

## Cost

Designed to run locally using free, open-source tools. No paid cloud services are required.

## Data Source

[NHTSA vPIC Vehicle API](https://vpic.nhtsa.dot.gov/api/)

## Disclaimer

This project is for educational and portfolio purposes. Vehicle catalog data does not represent vehicle sales or registrations.
