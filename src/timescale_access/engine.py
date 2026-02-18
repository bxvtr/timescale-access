from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_engine(db_url: str) -> Engine:
    """
    Create a SQLAlchemy Engine for the given database URL.

    Args:
        db_url (str): Database URL.

    Returns:
        Engine: SQLAlchemy engine instance used for database connections.
    """
    return create_engine(db_url)


def check_connection(engine: Engine) -> bool:
    """
    Test whether a connection to the database can be established.

    Args:
        engine (Engine): SQLAlchemy engine to test.

    Returns:
        bool: True if the connection test succeeds, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # Broad on purpose: any failure means "no connection"
        return False
