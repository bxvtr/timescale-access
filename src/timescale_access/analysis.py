import logging
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import MetaData, Table, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine


def get_missing_trade_seq(engine: Engine, schema_name: str, table_name: str) -> pd.DataFrame:
    """
    Return all expected but missing ``trade_seq`` values per ``instrument_name``.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name.
        table_name (str): Table name.

    Returns:
        pd.DataFrame: Missing sequence values per instrument.
    """
    query = text(
        f"""
        WITH seq_range AS (
            SELECT DISTINCT instrument_name,
                   MIN(trade_seq) AS min_seq,
                   MAX(trade_seq) AS max_seq
            FROM {schema_name}.{table_name}
            GROUP BY instrument_name
        ),
        all_numbers AS (
            SELECT instrument_name, generate_series(min_seq, max_seq) AS expected_seq
            FROM seq_range
        ),
        actual_numbers AS (
            SELECT DISTINCT instrument_name, trade_seq
            FROM {schema_name}.{table_name}
        )
        SELECT a.instrument_name, a.expected_seq
        FROM all_numbers a
        LEFT JOIN actual_numbers b
          ON a.instrument_name = b.instrument_name
         AND a.expected_seq = b.trade_seq
        WHERE b.trade_seq IS NULL;
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def get_nonconsecutive_trade_seq(
    engine: Engine,
    schema_name: str,
    table_name: str,
) -> pd.DataFrame:
    """
    Return all ``trade_seq`` rows where the sequence is not consecutive.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name.
        table_name (str): Table name.

    Returns:
        pd.DataFrame: Rows with gaps in ``trade_seq`` per instrument.
    """
    query = text(
        f"""
        WITH diffs AS (
            SELECT
                instrument_name,
                trade_seq,
                LAG(trade_seq) OVER (
                    PARTITION BY instrument_name
                    ORDER BY trade_seq
                ) AS previous_seq
            FROM {schema_name}.{table_name}
            WHERE trade_seq IS NOT NULL
        )
        SELECT *,
               trade_seq - previous_seq AS diff
        FROM diffs
        WHERE trade_seq - previous_seq != 1;
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def get_duplicate_rows(engine: Engine, schema_name: str, table_name: str) -> pd.DataFrame:
    """
    Return all rows where the combination (instrument_name, trade_seq) occurs multiple times.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name.
        table_name (str): Table name.

    Returns:
        pd.DataFrame: DataFrame containing all duplicate rows.
    """
    query = f"""
        SELECT *
        FROM {schema_name}.{table_name}
        WHERE (instrument_name, trade_seq) IN (
            SELECT instrument_name, trade_seq
            FROM {schema_name}.{table_name}
            GROUP BY instrument_name, trade_seq
            HAVING COUNT(*) > 1
        )
        ORDER BY instrument_name, trade_seq;
    """
    return pd.read_sql(query, engine)


def get_null_summary(engine: Engine, schema_name: str, table_name: str) -> pd.DataFrame:
    """
    Create (if necessary) and call a function that summarizes NULL values for any
    table in a schema.

    The function name is generated using the pattern:
    ``check_nulls_in_{schema_name}_{table_name}``.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name.
        table_name (str): Table name.

    Returns:
        pd.DataFrame: Summary of NULL counts per column and instrument name.
    """
    func_name = f"check_nulls_in_{schema_name}_{table_name}".lower()

    check_fn_query = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM pg_proc
            WHERE proname = :func_name
        );
        """
    )

    create_fn_sql = text(
        f"""
        CREATE OR REPLACE FUNCTION {func_name}()
        RETURNS TABLE(instrument_name text, column_name text, null_count bigint)
        LANGUAGE plpgsql AS
        $$
        DECLARE
            col record;
            dyn_sql text;
        BEGIN
            FOR col IN
                SELECT c.column_name
                FROM information_schema.columns c
                WHERE c.table_schema = '{schema_name}'
                  AND c.table_name = '{table_name}'
                  AND c.column_name != 'instrument_name'
            LOOP
                dyn_sql := format(
                    'SELECT instrument_name, %L AS column_name, COUNT(*) AS null_count
                     FROM {schema_name}.{table_name}
                     WHERE %I IS NULL
                     GROUP BY instrument_name
                     HAVING COUNT(*) > 0',
                    col.column_name, col.column_name
                );

                RETURN QUERY EXECUTE dyn_sql;
            END LOOP;
        END;
        $$;
        """
    )

    with engine.begin() as conn:
        exists = conn.execute(check_fn_query, {"func_name": func_name}).scalar()
        if not exists:
            conn.execute(create_fn_sql)

    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {func_name}();"))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


def get_hypertable_size(engine: Engine, schema_name: str, table_name: str) -> str:
    """
    Return the total size of a TimescaleDB hypertable as a formatted string
    (for example ``"123 MB"``).

    The implementation:
    1. Retrieves the internal hypertable ID from ``_timescaledb_catalog.hypertable``.
    2. Summarizes the size of all chunks in ``_timescaledb_internal``.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name, e.g. ``"raw_data"``.
        table_name (str): Hypertable name, e.g. ``"btc_weekly"``.

    Returns:
        str: Total formatted size (for example ``"512 MB"``, ``"3 GB"``).

    Raises:
        ValueError: If the hypertable cannot be found.
    """
    get_id_sql = text(
        """
        SELECT id
        FROM _timescaledb_catalog.hypertable
        WHERE schema_name = :schema_name AND table_name = :table_name
        """
    )

    with engine.connect() as conn:
        result = conn.execute(
            get_id_sql,
            {"schema_name": schema_name, "table_name": table_name},
        ).fetchone()
        if result is None:
            raise ValueError(f"Hypertable '{schema_name}.{table_name}' not found.")
        hypertable_id = result[0]

    get_size_sql = text(
        f"""
        SELECT pg_size_pretty(SUM(pg_total_relation_size(c.oid))) AS total_size
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = '_timescaledb_internal'
          AND c.relname LIKE '_hyper_{hypertable_id}_%%_chunk';
        """
    )

    with engine.connect() as conn:
        result = conn.execute(get_size_sql).fetchone()
        return result[0] if result else "0 bytes"


def get_row_count(engine: Engine, schema_name: str, table_name: str) -> int:
    """
    Return the number of rows in a table.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name (for example ``"raw_data"``).
        table_name (str): Table name (for example ``"btc_weekly"``).

    Returns:
        int: Number of rows in the table.
    """
    query = text(f"SELECT COUNT(*) FROM {schema_name}.{table_name}")
    with engine.connect() as conn:
        result = conn.execute(query).scalar()
        return int(result) if result is not None else 0


def insert_hypertable_on_conflict(
    engine: Engine,
    schema_name: str,
    table_name: str,
    df: pd.DataFrame,
    time_column: str,
) -> None:
    """
    Insert a DataFrame into a TimescaleDB hypertable and avoid duplicates via
    ``ON CONFLICT``.

    The function creates the table and columns as needed and ensures a UNIQUE
    index on ``(instrument_name, trade_seq, timestamp)``. All index columns must
    be present as columns in the DataFrame.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Target schema.
        table_name (str): Target table name.
        df (pd.DataFrame): Data to insert.
        time_column (str): Time column for TimescaleDB.
    """
    if df.empty:
        logging.info("No data to insert.")
        return

    with engine.begin() as conn:
        # Ensure table exists
        result = conn.execute(
            text(
                """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = :schema_name AND table_name = :table_name
            );
            """
            ),
            {"schema_name": schema_name, "table_name": table_name},
        ).scalar()

        if not result:
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
            conn.execute(
                text(
                    f"""
                CREATE TABLE {schema_name}.{table_name} (
                    {', '.join(cols_sql)}
                );
                """
                )
            )

        # Add missing columns
        existing_cols_result = conn.execute(
            text(
                """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema_name AND table_name = :table_name;
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

        # Ensure UNIQUE index
        index_name = f"unique_{table_name}_instrument_seq_ts"
        conn.execute(
            text(
                f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = :index_name
                      AND n.nspname = :schema_name
                ) THEN
                    EXECUTE 'CREATE UNIQUE INDEX {index_name}
                             ON {schema_name}.{table_name}
                             (instrument_name, trade_seq, {time_column})';
                END IF;
            END$$;
            """
            ),
            {"schema_name": schema_name, "index_name": index_name},
        )

    # Insert with ON CONFLICT DO NOTHING
    metadata = MetaData()
    table_obj = Table(table_name, metadata, autoload_with=engine, schema=schema_name)
    records: List[Dict[str, Any]] = df.to_dict(orient="records")

    with engine.begin() as conn:
        for record in records:
            stmt = insert(table_obj).values(**record)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["instrument_name", "trade_seq", time_column]
            )
            conn.execute(stmt)

        # Ensure hypertable
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
