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
from sqlalchemy import create_engine, text

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
SCHEMA = "raw"


def snake_case(name: str) -> str:
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    return name.strip("_").lower()


def build_engine():
    load_dotenv()
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


def load_csv(engine, csv_path: Path) -> tuple[str, int]:
    table_name = snake_case(csv_path.stem)
    df = pd.read_csv(csv_path)
    df.columns = [snake_case(col) for col in df.columns]
    df.to_sql(
        table_name,
        engine,
        schema=SCHEMA,
        if_exists="replace",
        index=False,
    )
    return table_name, len(df)


def main():
    csv_files = sorted(RAW_DATA_DIR.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {RAW_DATA_DIR}. Nothing to load.")
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
