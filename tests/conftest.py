"""Shared pytest fixtures for the test suite."""

from typing import Iterator

import pytest

from timescale_access.client import TimescaleAccess

from .config import DATABASE_URL


@pytest.fixture(scope="session")
def test_db() -> Iterator[TimescaleAccess]:
    """
    Provide a TimescaleAccess instance connected to the test database.

    The connection is created once per test session and disposed after all tests
    using this fixture have finished.
    """
    db = TimescaleAccess(DATABASE_URL)
    try:
        yield db
    finally:
        db.dispose_connection()
