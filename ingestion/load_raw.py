"""Load every CSV in data/raw/ into the `raw` schema of Postgres.

Each CSV becomes one table named after its filename (snake_cased, no
extension). Re-running is safe: each table is dropped and recreated from
the current CSV contents.
"""

import os
import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
SCHEMA = "raw"
REQUIRED_ENV_VARS = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")


def snake_case(name: str) -> str:
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    return name.strip("_").lower()


def build_engine():
    load_dotenv()
    missing = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        print(
            f"Missing required environment variable(s): {', '.join(missing)}.\n"
            "Copy .env.example to .env and fill in your Postgres connection details."
        )
        sys.exit(1)

    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )
    return create_engine(url)


def load_csv(engine, csv_path: Path) -> tuple[str, int]:
    table_name = snake_case(csv_path.stem)

    # Columns like zip code prefixes are numeric-looking but not numbers
    # (leading zeros matter); force them to stay as strings.
    header = pd.read_csv(csv_path, nrows=0).columns
    dtype = {col: str for col in header if "zip_code" in snake_case(col)}

    df = pd.read_csv(csv_path, dtype=dtype)
    df.columns = [snake_case(col) for col in df.columns]

    # Plain if_exists="replace" issues a bare DROP TABLE, which fails once
    # anything downstream (e.g. a dbt staging view) depends on this table.
    # Drop with CASCADE first so re-running ingestion after a dbt build
    # still works; dependent views just need `dbt run` again afterward.
    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS {SCHEMA}."{table_name}" CASCADE'))

    df.to_sql(
        table_name,
        engine,
        schema=SCHEMA,
        if_exists="replace",
        index=False,
        chunksize=10_000,
    )
    return table_name, len(df)


def main():
    csv_files = sorted(RAW_DATA_DIR.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {RAW_DATA_DIR}. Nothing to load.")
        sys.exit(1)

    table_names = [snake_case(p.stem) for p in csv_files]
    duplicates = {name for name in table_names if table_names.count(name) > 1}
    if duplicates:
        print(
            "Multiple CSV files map to the same table name after "
            f"snake_casing: {', '.join(sorted(duplicates))}. Rename the "
            "source files so each maps to a distinct table."
        )
        sys.exit(1)

    engine = build_engine()
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))

    print(f"Loading {len(csv_files)} CSV file(s) into schema '{SCHEMA}'...\n")
    summary = []
    for csv_path in csv_files:
        table_name, row_count = load_csv(engine, csv_path)
        summary.append((table_name, row_count))
        print(f"  {SCHEMA}.{table_name:<40} {row_count:>8} rows")

    total_rows = sum(count for _, count in summary)
    print(f"\nDone. {len(summary)} table(s) loaded, {total_rows} rows total.")


if __name__ == "__main__":
    main()
