from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.engine import Engine

from . import analysis, engine, read, write


class TimescaleAccess:
    """
    Convenience wrapper around database operations using SQLAlchemy.
    """

    def __init__(self, db_url: str) -> None:
        """
        Initialize a database connection using the ``connection`` module.

        Args:
            db_url (str): Database URL.
        """
        self.engine: Engine = engine.get_engine(db_url)

    def dispose_connection(self) -> None:
        """
        Explicitly dispose the underlying SQLAlchemy engine and free resources.
        """
        self.engine.dispose()

    def check_connection(self) -> bool:
        """
        Test whether a connection to the database can be established.

        Returns:
            bool: True if the connection check succeeds, False otherwise.
        """
        return engine.check_connection(self.engine)

    def insert_hypertable(
        self,
        schema_name: str,
        table_name: str,
        df: pd.DataFrame,
        index: bool = False,
        chunksize: int = 500,
        time_column: str = "timestamp",
    ) -> None:
        """
        Insert a pandas DataFrame into a TimescaleDB hypertable.

        This method is tailored to time-series data. If the target table does not exist,
        it is automatically created as a TimescaleDB hypertable. The time column is
        set to ``"timestamp"`` by default.

        Args:
            schema_name (str): Name of the target schema.
            table_name (str): Name of the target table.
            df (pd.DataFrame): DataFrame to insert. Must contain a time column.
            index (bool, optional): Whether to persist the pandas index (default: False).
            chunksize (int, optional): Number of rows per batch insert (default: 500).
            time_column (str, optional): Name of the time column in the DataFrame
                (default: ``"timestamp"``).

        Raises:
            ValueError: If the given time column is not present in ``df``.
            RuntimeError: If insertion or hypertable creation fails.
        """
        write.insert_hypertable(
            engine=self.engine,
            schema_name=schema_name,
            table_name=table_name,
            df=df,
            index=index,
            chunksize=chunksize,
            time_column=time_column,
        )

    def drop_table(self, schema_name: str, table_name: str) -> None:
        """
        Drop a table in the given schema.

        Args:
            schema_name (str): Schema name.
            table_name (str): Name of the table to drop.
        """
        write.drop_table(self.engine, schema_name, table_name)

    def get_existing_timestamps(
        self,
        schema_name: str,
        table_name: str,
        column: str = "timestamp",
    ) -> List[datetime]:
        """
        Return a sorted list of distinct timestamps from a specific column.

        Args:
            schema_name (str): Schema name.
            table_name (str): Table name.
            column (str, optional): Column name to query (default: ``"timestamp"``).

        Returns:
            List[datetime]: Sorted list of timestamps.
        """
        return read.get_existing_timestamps(self.engine, schema_name, table_name, column)

    def get_table_names(self, schema_name: str) -> List[str]:
        """
        Return all table names in the given schema.

        Args:
            schema_name (str): Schema name.

        Returns:
            List[str]: List of table names.
        """
        return read.get_table_names(self.engine, schema_name)

    def get_column_names(self, schema_name: str, table_name: str) -> List[str]:
        """
        Return all column names for a given table.

        Args:
            schema_name (str): Schema name.
            table_name (str): Table name.

        Returns:
            List[str]: List of column names.
        """
        return read.get_column_names(self.engine, schema_name, table_name)

    def get_distinct_values(
        self,
        schema_name: str,
        table_name: str,
        column_name: str,
    ) -> List[str]:
        """
        Return all distinct values of a column in a table.

        Args:
            schema_name (str): Schema name.
            table_name (str): Table name.
            column_name (str): Column name.

        Returns:
            List[str]: List of distinct values in the column.
        """
        return read.get_distinct_values(self.engine, schema_name, table_name, column_name)

    def get_indexes(self, schema_name: str, table_name: str) -> List[Dict[str, Any]]:
        """
        Return all indexes for a given table.

        Args:
            schema_name (str): Schema name.
            table_name (str): Table name.

        Returns:
            List[dict]: List of index metadata dictionaries.
        """
        return read.get_indexes(self.engine, schema_name, table_name)

    def get_table(
        self,
        schema_name: str,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Load a table as a pandas DataFrame with optional filters.

        Args:
            schema_name (str): Schema name.
            table_name (str): Table name.
            filters (Optional[Dict[str, Any]], optional): Filter specification for the
                WHERE clause.
                Examples:
                    - Single/multiple values:
                      ``{"instrument_name": ["BTC-14MAR25", "ETH-14MAR25"]}``
                    - Range filter:
                      ``{"trade_seq": {"between": (100, 200)}}``

        Returns:
            pd.DataFrame: Filtered table contents.
        """
        return read.get_table(self.engine, schema_name, table_name, filters)

    def get_databases(self) -> List[str]:
        """
        Return all non-template databases in the PostgreSQL instance.

        Returns:
            List[str]: List of database names.
        """
        return read.get_databases(self.engine)

    def get_roles(self) -> List[Dict[str, Any]]:
        """
        Return all roles and their privileges.

        Returns:
            List[dict]: List of role metadata, including superuser and createdb flags.
        """
        return read.get_roles(self.engine)

    def get_role_memberships(self) -> List[Dict[str, Any]]:
        """
        Return all role memberships in the database.

        Returns:
            List[dict]: List of mappings from member to role.
        """
        return read.get_role_memberships(self.engine)

    def get_active_connections(self) -> List[Dict[str, Any]]:
        """
        Return information about active database connections.

        Returns:
            List[dict]: List of active connections with database name, user and client IP.
        """
        return read.get_active_connections(self.engine)

    def get_schemas(self) -> List[str]:
        """
        Return a list of all user-defined schemas.

        Returns:
            List[str]: List of schema names.
        """
        return read.get_schemas(self.engine)

    def ensure_schema_exists(self, schema_name: str) -> None:
        """
        Create the given schema if it does not already exist.

        Args:
            schema_name (str): Name of the schema to ensure.
        """
        write.ensure_schema_exists(self.engine, schema_name)

    def get_missing_trade_seq(self, schema_name: str, table_name: str) -> pd.DataFrame:
        """
        Return all expected but missing ``trade_seq`` values per ``instrument_name``.

        Args:
            schema_name (str): Schema name.
            table_name (str): Table name.

        Returns:
            pd.DataFrame: Rows describing missing sequence values per instrument.
        """
        return analysis.get_missing_trade_seq(self.engine, schema_name, table_name)

    def get_nonconsecutive_trade_seq(
        self,
        schema_name: str,
        table_name: str,
    ) -> pd.DataFrame:
        """
        Return all ``trade_seq`` rows where the sequence is not consecutive.

        Args:
            schema_name (str): Schema name.
            table_name (str): Table name.

        Returns:
            pd.DataFrame: Rows with gaps in ``trade_seq`` per instrument.
        """
        return analysis.get_nonconsecutive_trade_seq(self.engine, schema_name, table_name)

    def get_duplicate_rows(self, schema_name: str, table_name: str) -> pd.DataFrame:
        """
        Return all duplicate rows where ``(instrument_name, trade_seq)`` occurs multiple times.

        Args:
            schema_name (str): Schema name.
            table_name (str): Table name.

        Returns:
            pd.DataFrame: DataFrame containing all duplicate rows.
        """
        return analysis.get_duplicate_rows(self.engine, schema_name, table_name)

    def get_null_summary(self, schema_name: str, table_name: str) -> pd.DataFrame:
        """
        Create (if necessary) and invoke a function that summarizes NULL values in a table.

        The created function is named according to the pattern:
        ``check_nulls_in_{schema_name}_{table_name}``.

        Args:
            schema_name (str): Schema name.
            table_name (str): Table name.

        Returns:
            pd.DataFrame: Summary of NULL counts per column and instrument name.
        """
        return analysis.get_null_summary(self.engine, schema_name, table_name)

    def get_hypertable_size(self, schema_name: str, table_name: str) -> str:
        """
        Return the total size of a TimescaleDB hypertable as a formatted string
        (for example ``"123 MB"``).

        The implementation:
        1. Retrieves the internal hypertable ID from ``_timescaledb_catalog.hypertable``.
        2. Summarizes the size of all chunks in ``_timescaledb_internal``.

        Args:
            schema_name (str): Schema name of the hypertable (for example ``"raw_data"``).
            table_name (str): Hypertable name (for example ``"btc_weekly"``).

        Returns:
            str: Total size formatted by ``pg_size_pretty`` (for example ``"512 MB"``, ``"3 GB"``).

        Raises:
            ValueError: If the hypertable cannot be found.
        """
        return analysis.get_hypertable_size(self.engine, schema_name, table_name)

    def get_row_count(self, schema_name: str, table_name: str) -> int:
        """
        Return the number of rows in a table.

        Args:
            schema_name (str): Schema name (for example ``"raw_data"``).
            table_name (str): Table name (for example ``"btc_weekly"``).

        Returns:
            int: Number of rows in the table.
        """
        return analysis.get_row_count(self.engine, schema_name, table_name)

    def insert_hypertable_on_conflict(
        self,
        schema_name: str,
        table_name: str,
        df: pd.DataFrame,
        time_column: str = "timestamp",
    ) -> None:
        """
        Insert a DataFrame into a TimescaleDB hypertable and avoid duplicates via
        ``ON CONFLICT``.

        The function creates the table and columns as needed and ensures a UNIQUE index on
        ``(instrument_name, trade_seq, timestamp)``. All index columns must be present in
        the DataFrame.

        Args:
            schema_name (str): Target schema.
            table_name (str): Target table name.
            df (pd.DataFrame): Data to insert.
            time_column (str): Name of the time column used by TimescaleDB.
        """
        analysis.insert_hypertable_on_conflict(
            self.engine,
            schema_name,
            table_name,
            df,
            time_column,
        )
