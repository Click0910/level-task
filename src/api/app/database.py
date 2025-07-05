import os
from contextlib import contextmanager
from typing import List, Any, Dict, Optional

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    JSON,
    TIMESTAMP
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.future import select

import logging

logger = logging.getLogger(__name__)

# Declarative Base for ORM
Base = declarative_base()


class Ticket(Base):
    __tablename__ = "customer_support_tickets"

    ticket_id = Column(String, primary_key=True)
    subject = Column(String)
    body = Column(String)
    answer = Column(String)
    type = Column(String)
    queue = Column(String)
    priority = Column(String)
    language = Column(String)
    tags = Column(String)
    predicted_category = Column(String)
    confidence = Column(Float)
    summary = Column(String)
    processed_at = Column(String)
    ground_truth_category = Column(String)


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
