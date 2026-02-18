"""Static configuration values used in the test suite."""

import os

# The database URL used by the tests.
# In CI, this is typically provided via the DATABASE_URL environment variable.
# Locally (e.g. inside the devcontainer with docker-compose), the default
# points at the "db" service defined in docker-compose.yaml.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://superuser:supersecret@db:5432/postgres",
)

SCHEMA = "test_schema"
TEST_TABLE_1 = "test_table_1"
TEST_TABLE_2 = "test_table_2"
TEST_TABLE_3 = "test_table_3"
