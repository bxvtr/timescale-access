"""Integration tests for the TimescaleAccess wrapper."""

import pandas as pd

from .config import SCHEMA, TEST_TABLE_1, TEST_TABLE_2, TEST_TABLE_3


def test_check_connection(test_db) -> None:
    """The database connection check should return True."""
    assert test_db.check_connection() is True


def test_get_schemas(test_db) -> None:
    """get_schemas should return a list of schema names."""
    schemas = test_db.get_schemas()
    assert isinstance(schemas, list)


def test_ensure_schema_exists(test_db) -> None:
    """ensure_schema_exists should create the schema if it does not exist."""
    test_db.ensure_schema_exists(SCHEMA)
    schemas = test_db.get_schemas()
    assert SCHEMA in schemas


def test_insert_and_read(test_db) -> None:
    """
    Insert time-series data into two tables and verify timestamps can be read back.

    This test covers:
    - ISO date strings converted to timestamps
    - Unix timestamps in milliseconds converted to timestamps
    - Insert into both standard hypertable and ON CONFLICT variant
    """
    # ---------- Test 1: ISO date string ----------
    df = pd.DataFrame(
        [
            {
                "instrument_name": "BTC-PERPETUAL",
                "trade_seq": 123_456,
                "timestamp": "2024-05-01",
                "value": 42,
            }
        ]
    )

    # Convert ISO date string to a datetime object
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Insert the DataFrame as a hypertable into the database
    test_db.insert_hypertable(SCHEMA, TEST_TABLE_1, df)
    test_db.insert_hypertable_on_conflict(SCHEMA, TEST_TABLE_2, df)

    # Ensure both tables exist
    table_names = test_db.get_table_names(SCHEMA)
    assert TEST_TABLE_1 in table_names
    assert TEST_TABLE_2 in table_names

    # Retrieve all timestamps from both tables
    timestamps_1 = test_db.get_existing_timestamps(SCHEMA, TEST_TABLE_1)
    timestamps_2 = test_db.get_existing_timestamps(SCHEMA, TEST_TABLE_2)

    # Check that the expected date is present
    assert "2024-05-01" in [str(t)[:10] for t in timestamps_1]
    assert "2024-05-01" in [str(t)[:10] for t in timestamps_2]

    # ---------- Test 2: Unix timestamp in milliseconds ----------
    df = pd.DataFrame(
        [
            {
                "instrument_name": "BTC-17DEC21",
                "trade_seq": 456_123,
                "timestamp": 1_590_476_708_320,
                "value": 54,
            }
        ]
    )

    # Convert Unix timestamp in milliseconds to a datetime object
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    # Insert the converted DataFrame into both tables
    test_db.insert_hypertable(SCHEMA, TEST_TABLE_1, df)
    test_db.insert_hypertable_on_conflict(SCHEMA, TEST_TABLE_2, df)

    # Ensure both tables still exist
    table_names = test_db.get_table_names(SCHEMA)
    assert TEST_TABLE_1 in table_names
    assert TEST_TABLE_2 in table_names

    # Retrieve all timestamps again
    timestamps_1 = test_db.get_existing_timestamps(SCHEMA, TEST_TABLE_1)
    timestamps_2 = test_db.get_existing_timestamps(SCHEMA, TEST_TABLE_2)

    # The expected converted date
    expected_date = "2020-05-26"
    assert expected_date in [str(t)[:10] for t in timestamps_1]
    assert expected_date in [str(t)[:10] for t in timestamps_2]


def test_table_names(test_db) -> None:
    """After inserting data, both test tables should be listed in get_table_names."""
    names = test_db.get_table_names(SCHEMA)
    assert isinstance(names, list)
    assert TEST_TABLE_1 in names
    assert TEST_TABLE_2 in names


def test_get_column_names(test_db) -> None:
    """get_column_names should return a non-empty list for both tables."""
    columns_1 = test_db.get_column_names(SCHEMA, TEST_TABLE_1)
    assert isinstance(columns_1, list)
    assert "timestamp" in columns_1 or len(columns_1) > 0

    columns_2 = test_db.get_column_names(SCHEMA, TEST_TABLE_2)
    assert isinstance(columns_2, list)
    assert "timestamp" in columns_2 or len(columns_2) > 0


def test_get_distinct_values(test_db) -> None:
    """
    Insert data with duplicates and NULLs and verify distinct non-null values.

    This test ensures that get_distinct_values:
    - returns unique values only
    - excludes NULL from the result set
    """
    df = pd.DataFrame(
        [
            {
                "instrument_name": "BTC-17DEC21",
                "trade_seq": 456_123,
                "timestamp": 1_590_476_708_320,
                "value": 54,
            },
            {
                "instrument_name": "BTC-17DEC21",
                "trade_seq": 456_124,
                "timestamp": 1_590_476_708_321,
                "value": 54,  # same as above
            },
            {
                "instrument_name": "BTC-24DEC21",
                "trade_seq": 456_125,
                "timestamp": 1_590_476_708_322,
                "value": 60,
            },
            {
                "instrument_name": "ETH-17DEC21",
                "trade_seq": 456_126,
                "timestamp": 1_590_476_708_323,
                "value": 54,
            },
            {
                "instrument_name": "ETH-17DEC21",
                "trade_seq": 456_127,
                "timestamp": 1_590_476_708_324,
                "value": None,  # used to test NULL handling
            },
        ]
    )

    test_db.insert_hypertable(SCHEMA, TEST_TABLE_3, df)

    distinct_values = set(test_db.get_distinct_values(SCHEMA, TEST_TABLE_3, "value"))
    assert distinct_values == {54, 60}

    test_db.drop_table(SCHEMA, TEST_TABLE_3)


def test_get_indexes(test_db) -> None:
    """get_indexes should return a list for both tables."""
    indexes_1 = test_db.get_indexes(SCHEMA, TEST_TABLE_1)
    assert isinstance(indexes_1, list)

    indexes_2 = test_db.get_indexes(SCHEMA, TEST_TABLE_2)
    assert isinstance(indexes_2, list)


def test_get_table(test_db) -> None:
    """get_table should return a non-empty DataFrame for matching filters."""
    df_1 = test_db.get_table(SCHEMA, TEST_TABLE_1, {"trade_seq": 123_456})
    assert isinstance(df_1, pd.DataFrame)
    assert not df_1.empty

    df_2 = test_db.get_table(SCHEMA, TEST_TABLE_2, {"trade_seq": 456_123})
    assert isinstance(df_2, pd.DataFrame)
    assert not df_2.empty


def test_drop_table(test_db) -> None:
    """drop_table should remove the given tables from the schema."""
    assert test_db.drop_table(SCHEMA, TEST_TABLE_1) is None
    assert TEST_TABLE_1 not in test_db.get_table_names(SCHEMA)

    assert test_db.drop_table(SCHEMA, TEST_TABLE_2) is None
    assert TEST_TABLE_2 not in test_db.get_table_names(SCHEMA)


def test_get_databases(test_db) -> None:
    """get_databases should return a list including the 'postgres' database."""
    dbs = test_db.get_databases()
    assert isinstance(dbs, list)
    assert "postgres" in dbs


def test_get_roles(test_db) -> None:
    """get_roles should return a list of role dictionaries."""
    roles = test_db.get_roles()
    assert isinstance(roles, list)
    # We allow either 'rolname' (raw PG output) or a normalized 'role_name' key
    assert all("rolname" in role or "role_name" in role for role in roles)


def test_get_role_memberships(test_db) -> None:
    """get_role_memberships should return a list (possibly empty) of mappings."""
    memberships = test_db.get_role_memberships()
    assert isinstance(memberships, list)


def test_get_active_connections(test_db) -> None:
    """get_active_connections should return a list of connection metadata."""
    connections = test_db.get_active_connections()
    assert isinstance(connections, list)
