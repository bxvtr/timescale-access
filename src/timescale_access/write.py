from typing import List

import pandas as pd
from sqlalchemy import Engine, text
from sqlalchemy.dialects.postgresql import TIMESTAMP


def insert_hypertable(
    engine: Engine,
    schema_name: str,
    table_name: str,
    df: pd.DataFrame,
    index: bool = False,
    chunksize: int = 1000,
    time_column: str = "timestamp",
) -> None:
    """
    Insert a pandas DataFrame into a TimescaleDB hypertable.

    The table and its columns are created automatically if they do not exist yet.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Target schema name.
        table_name (str): Target table name.
        df (pd.DataFrame): Data to insert.
        index (bool): Whether to persist the DataFrame index.
        chunksize (int): Batch size for inserts.
        time_column (str): Name of the time column.
    """
    if time_column not in df.columns:
        raise ValueError(f"Column '{time_column}' not found in DataFrame.")

    with engine.begin() as conn:
        # Check whether table exists
        result = conn.execute(
            text(
                """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = :schema_name
                  AND table_name = :table_name
            );
            """
            ),
            {"schema_name": schema_name, "table_name": table_name},
        ).scalar()

        if not result:
            # Table does not exist: create it based on df columns and dtypes
            cols_sql: List[str] = []
            for col in df.columns:
                dtype = df[col].dtype
                if pd.api.types.is_integer_dtype(dtype):
                    sql_type = "BIGINT"
                elif pd.api.types.is_float_dtype(dtype):
                    sql_type = "NUMERIC"
                elif pd.api.types.is_datetime64_any_dtype(dtype):
                    sql_type = "TIMESTAMP"
                else:
                    sql_type = "TEXT"
                cols_sql.append(f"{col} {sql_type}")

            create_stmt = f"""
                CREATE TABLE {schema_name}.{table_name} (
                    {', '.join(cols_sql)}
                );
            """
            conn.execute(text(create_stmt))
        else:
            # Table exists: add any missing columns
            existing_cols_result = conn.execute(
                text(
                    """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema_name
                  AND table_name = :table_name;
                """
                ),
                {"schema_name": schema_name, "table_name": table_name},
            ).fetchall()

            existing_cols = {row[0] for row in existing_cols_result}
            for col in df.columns:
                if col not in existing_cols:
                    dtype = df[col].dtype
                    if pd.api.types.is_integer_dtype(dtype):
                        sql_type = "BIGINT"
                    elif pd.api.types.is_float_dtype(dtype):
                        sql_type = "NUMERIC"
                    elif pd.api.types.is_datetime64_any_dtype(dtype):
                        sql_type = "TIMESTAMP"
                    else:
                        sql_type = "TEXT"
                    conn.execute(
                        text(
                            f"""
                        ALTER TABLE {schema_name}.{table_name}
                        ADD COLUMN {col} {sql_type};
                        """
                        )
                    )

    # Insert DataFrame
    try:
        df.to_sql(
            name=table_name,
            con=engine,
            schema=schema_name,
            if_exists="append",
            index=index,
            chunksize=chunksize,
            method="multi",
            dtype={time_column: TIMESTAMP()},
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Error inserting into table '{schema_name}.{table_name}': {exc}"
        ) from exc

    # Ensure hypertable
    with engine.begin() as conn:
        hypertable_exists = conn.execute(
            text(
                """
            SELECT 1
            FROM timescaledb_information.hypertables
            WHERE hypertable_schema = :schema_name
              AND hypertable_name = :table_name;
            """
            ),
            {"schema_name": schema_name, "table_name": table_name},
        ).fetchone()

        if not hypertable_exists:
            conn.execute(
                text(
                    f"""
                SELECT create_hypertable(
                    '{schema_name}.{table_name}'::regclass,
                    '{time_column}',
                    migrate_data => TRUE,
                    if_not_exists => TRUE
                );
                """
                )
            )


def drop_table(engine: Engine, schema_name: str, table_name: str) -> None:
    """
    Drop a table in the given schema.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name.
        table_name (str): Target table name.
    """
    full_table = f"{schema_name}.{table_name}"
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {full_table} CASCADE;"))


def ensure_schema_exists(engine: Engine, schema_name: str) -> None:
    """
    Create the given schema if it does not already exist.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name to ensure.
    """
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name};"))
        conn.commit()
