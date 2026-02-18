from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def get_existing_timestamps(
    engine: Engine,
    schema_name: str,
    table_name: str,
    column: str,
) -> List[datetime]:
    """
    Return a sorted list of distinct timestamps from a given column.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name.
        table_name (str): Table name.
        column (str): Column name.

    Returns:
        List[datetime]: Sorted list of timestamps.
    """
    full_table = f"{schema_name}.{table_name}"
    query = text(f"SELECT DISTINCT {column} FROM {full_table} ORDER BY {column}")
    with engine.connect() as conn:
        result = conn.execute(query)
        return [row[0] for row in result]


def get_table_names(engine: Engine, schema_name: str) -> List[str]:
    """
    Return all table names in a given schema.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name.

    Returns:
        List[str]: List of table names.
    """
    return inspect(engine).get_table_names(schema_name)


def get_column_names(engine: Engine, schema_name: str, table_name: str) -> List[str]:
    """
    Return all column names of a given table.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name.
        table_name (str): Table name.

    Returns:
        List[str]: List of column names.
    """
    inspector = inspect(engine)
    return [col["name"] for col in inspector.get_columns(table_name, schema_name)]


def get_distinct_values(
    engine: Engine,
    schema_name: str,
    table_name: str,
    column_name: str,
) -> List[str]:
    """
    Return all distinct, non-null values of a column in a table.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name.
        table_name (str): Table name.
        column_name (str): Column name.

    Returns:
        List[str]: List of distinct values in the column.
    """
    query = text(
        f"""
        SELECT DISTINCT "{column_name}"
        FROM "{schema_name}"."{table_name}"
        WHERE "{column_name}" IS NOT NULL
        """
    )
    with engine.connect() as conn:
        result = conn.execute(query)
        return [row[0] for row in result]


def get_indexes(engine: Engine, schema_name: str, table_name: str) -> List[Dict[str, Any]]:
    """
    Return index information for a given table.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name.
        table_name (str): Table name.

    Returns:
        List[dict]: List of index metadata dictionaries.
    """
    inspector = inspect(engine)
    return inspector.get_indexes(table_name, schema_name)


def get_table(
    engine: Engine,
    schema_name: str,
    table_name: str,
    filters: Optional[Dict[str, Union[Any, Dict[str, Any]]]] = None,
) -> pd.DataFrame:
    """
    Load a table as a pandas DataFrame with optional filter conditions.

    Args:
        engine (Engine): SQLAlchemy engine.
        schema_name (str): Schema name.
        table_name (str): Table name.
        filters (Optional[Dict[str, Union[Any, Dict[str, Any]]]], optional):
            Filter specification for the WHERE clause.

            Examples:
                - Single/multiple values:
                  ``{"instrument_name": ["BTC-14MAR25", "ETH-14MAR25"]}``
                - Range filter:
                  ``{"trade_seq": {"between": (100, 200)}}``

    Returns:
        pd.DataFrame: Filtered table.
    """
    full_table = f"{schema_name}.{table_name}"
    base_query = f"SELECT * FROM {full_table}"

    conditions: List[str] = []

    if filters:
        for column, value in filters.items():
            # Range filter
            if isinstance(value, dict) and "between" in value:
                low, high = value["between"]
                conditions.append(f"{column} BETWEEN {low} AND {high}")
            # Multiple values (IN)
            elif isinstance(value, (list, tuple, set)):
                value_list = ", ".join(
                    f"'{v}'" if isinstance(v, str) else str(v) for v in value
                )
                conditions.append(f"{column} IN ({value_list})")
            # Single equality
            else:
                value_str = f"'{value}'" if isinstance(value, str) else str(value)
                conditions.append(f"{column} = {value_str}")

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    query = base_query + where_clause + " ORDER BY trade_seq"

    return pd.read_sql(query, engine)


def get_databases(engine: Engine) -> List[str]:
    """
    Return all non-template databases in the PostgreSQL instance.

    Args:
        engine (Engine): SQLAlchemy engine.

    Returns:
        List[str]: List of database names.
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT datname FROM pg_database WHERE datistemplate = false;")
        )
        return [row[0] for row in result]


def get_roles(engine: Engine) -> List[Dict[str, Any]]:
    """
    Return all roles and their basic privileges.

    Args:
        engine (Engine): SQLAlchemy engine.

    Returns:
        List[dict]: List of dictionaries with role metadata.
    """
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
            SELECT rolname, rolsuper, rolcreaterole, rolcreatedb
            FROM pg_roles;
            """
            )
        )
        return [dict(row._mapping) for row in result]


def get_role_memberships(engine: Engine) -> List[Dict[str, Any]]:
    """
    Return all role memberships in the database.

    Args:
        engine (Engine): SQLAlchemy engine.

    Returns:
        List[dict]: List of mappings from member to role.
    """
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
            SELECT
                r.rolname AS role_name,
                m.rolname AS member_name
            FROM pg_auth_members am
            JOIN pg_roles r ON r.oid = am.roleid
            JOIN pg_roles m ON m.oid = am.member;
            """
            )
        )
        return [dict(row._mapping) for row in result]


def get_active_connections(engine: Engine) -> List[Dict[str, Any]]:
    """
    Return information about active database connections.

    Args:
        engine (Engine): SQLAlchemy engine.

    Returns:
        List[dict]: List of active connections with database name, user and client IP.
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT datname, usename, client_addr FROM pg_stat_activity;")
        )
        return [dict(row._mapping) for row in result]


def get_schemas(engine: Engine) -> List[str]:
    """
    Return a list of user-defined schemas, excluding system and TimescaleDB internals.

    Args:
        engine (Engine): SQLAlchemy engine.

    Returns:
        List[str]: List of schema names.
    """
    ignored_schemas = (
        "pg_catalog",
        "information_schema",
        "pg_toast",
        "timescaledb_information",
        "timescaledb_experimental",
        "_timescaledb_internal",
        "_timescaledb_functions",
        "_timescaledb_debug",
        "_timescaledb_config",
        "_timescaledb_catalog",
        "_timescaledb_cache",
    )

    query = text(
        """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN :ignored;
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query, {"ignored": ignored_schemas})
        return [row[0] for row in result]
