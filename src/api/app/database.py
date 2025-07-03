import os
from contextlib import contextmanager
from typing import List, Any, Dict

import sqlalchemy
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    select,
    and_,
    insert
)

from celery.utils.log import get_logger

logger = get_logger(__name__)

metadata = MetaData()

tickets = Table(
    "customer_support_tickets",
    metadata,
    sqlalchemy.Column("ticket_id", sqlalchemy.String),
    sqlalchemy.Column("subject", sqlalchemy.String),
    sqlalchemy.Column("body", sqlalchemy.String),
    sqlalchemy.Column("answer", sqlalchemy.String),
    sqlalchemy.Column("type", sqlalchemy.String),
    sqlalchemy.Column("queue", sqlalchemy.String),
    sqlalchemy.Column("priority", sqlalchemy.String),
    sqlalchemy.Column("language", sqlalchemy.String),
    sqlalchemy.Column("tags", sqlalchemy.String),
    sqlalchemy.Column("predicted_category", sqlalchemy.String),
    sqlalchemy.Column("confidence", sqlalchemy.String),
    sqlalchemy.Column("summary", sqlalchemy.String),
    sqlalchemy.Column("processed_at", sqlalchemy.String),
    sqlalchemy.Column("ground_truth_category", sqlalchemy.String),
)


def get_engine():
    """
    Factory singleton that provides a single database engine instance.

    Creates and maintains a single SQLAlchemy engine instance using connection pooling.
    Subsequent calls return the same engine instance. Configures pool settings for
    production environments.

    Returns:
        sqlalchemy.engine.Engine: SQLAlchemy database engine instance

    Notes:
        - Uses DATABASE_URL environment variable for connection string
        - Connection pool configuration:
          * pool_size=20 (max idle connections)
          * max_overflow=10 (temporary max connections beyond pool_size)
          * pool_pre_ping=True (validate connections before use)
        - Implements singleton pattern to prevent multiple engine instances

    Example:
        engine = get_engine()
    """
    if not hasattr(get_engine, "engine"):
        DATABASE_URL = os.environ["DATABASE_URL"]
        get_engine.engine = create_engine(
            DATABASE_URL,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True
        )
    return get_engine.engine


@contextmanager
def get_db_connection():
    """
    Context manager for obtaining and automatically releasing database connections.

    Provides safe connection handling by ensuring proper cleanup after use. Connections
    are acquired from the engine's connection pool and returned when context exits.

    Yields:
        sqlalchemy.engine.Connection: Active database connection

    Example:
        with get_db_connection() as conn:
            result = conn.execute(query)
    """
    engine = get_engine()
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()


def fetch_record(ticket_id: str) -> Dict[str, Any]:
    """
    Fetch a specific ticket in the DB
    """
    try:
        query = select(tickets).where(tickets.c.ticket_id == ticket_id)

        with get_db_connection() as conn:
            result = conn.execute(query).fetchone()
            return dict(result._mapping) if result else None

    except Exception as e:
        logger.error(f"Finding Error {ticket_id}: {str(e)}")
        raise


def filter_tickets_category(category: str) -> List[Dict[str, Any]]:
    try:
        query = select(tickets).where(tickets.c.predicted_category == category)
        with get_db_connection() as conn:
            results = conn.execute(query).fetchall()
            return [dict(row._mapping) for row in results]
    except Exception as e:
        raise e
