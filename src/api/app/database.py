import os
from contextlib import contextmanager
from typing import List, Any, Dict, Optional

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    TIMESTAMP,
    BigInteger,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.future import select

import logging

logger = logging.getLogger(__name__)

# Declarative Base for ORM
Base = declarative_base()


class Ticket(Base):
    __tablename__ = "customer_support_tickets"

    ticket_id = Column(BigInteger, primary_key=True, autoincrement=True)
    subject = Column(Text)
    body = Column(Text)
    answer = Column(Text)
    type = Column(String(50))
    queue = Column(String(50))
    priority = Column(String(20))
    language = Column(String(10))
    tags = Column(JSONB)

    predicted_category = Column(String(50))
    confidence = Column(Float)
    summary = Column(Text)
    processed_at = Column(TIMESTAMP)

    ground_truth_category = Column(String(50))

    __table_args__ = (
        Index("idx_queue", "queue"),
        Index("idx_priority", "priority"),
        Index("idx_predicted_category", "predicted_category"),
        Index("idx_ground_truth", "ground_truth_category"),
        Index("idx_processed_at", "processed_at"),
    )


def get_engine():
    if not hasattr(get_engine, "engine"):
        DATABASE_URL = os.environ["DATABASE_URL"]
        get_engine.engine = create_engine(
            DATABASE_URL,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            future=True
        )
    return get_engine.engine


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


@contextmanager
def get_db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def fetch_record(ticket_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a specific ticket by ID using ORM
    """
    try:
        with get_db_session() as session:
            result = session.execute(
                select(Ticket).where(Ticket.ticket_id == ticket_id)
            ).scalar_one_or_none()

            return result.__dict__ if result else None

    except Exception as e:
        logger.error(f"Finding Error {ticket_id}: {str(e)}")
        raise


def filter_tickets_category(category: str) -> List[Dict[str, Any]]:
    """
    Fetch all tickets with a given predicted category using ORM
    """
    try:
        with get_db_session() as session:
            results = session.execute(
                select(Ticket).where(Ticket.predicted_category == category)
            ).scalars().all()

            return [ticket.__dict__ for ticket in results]

    except Exception as e:
        logger.error(f"Filtering Error for category {category}: {str(e)}")
        raise
