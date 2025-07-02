import os
from typing import Any, Dict

from celery.utils.log import get_logger
from celery import Celery
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from sqlalchemy import create_engine, update, Table, MetaData

logger = get_logger(__name__)

inference = Celery(
    "inference",
    broker=os.getenv("BROKER_URL"),
    backend=os.getenv("REDIS_URL"),
)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
metadata = MetaData()

customer_support_tickets = Table(
    "customer_support_tickets",
    metadata, autoload_with=engine
)

PIPELINE_PATH = os.getenv("PIPELINE_PATH", "/workers/models/pipeline.joblib")
pipeline = joblib.load(PIPELINE_PATH)


def map_queue_to_category(queue: str) -> str:
    queue = queue.lower()
    if "technical support" in queue or "it support" in queue:
        return "technical"
    elif "billing" in queue or "payment" in queue:
        return "billing"
    else:
        return "general"


def update_ticket(
        ticket_id: str,
        predicted_category: str,
        confidence: float,
        ground_truth_category: str
):
    with engine.begin() as conn:
        stmt = (
            update(customer_support_tickets)
            .where(customer_support_tickets.c.ticket_id == ticket_id)
            .values(
                predicted_category=predicted_category,
                confidence=confidence,
                ground_truth_category=ground_truth_category,
                processed_at="now()"
            )
        )
        conn.execute(stmt)


@inference.task(bind=True, name="run_inference", acks_late=True, queue="inference_queue")
def inference_task(self, **kwargs):
    logger.info(f"Startinf inference by {kwargs}")
    self.update_state(state="STARTED", meta={"step": "reading_metadata"})

    payload = kwargs

    input_text = f"{payload['subject']} {payload['body']}"
    predicted_proba = pipeline.predict_proba([input_text])[0]
    predicted_class = pipeline.classes_[np.argmax(predicted_proba)]
    confidence = float(np.max(predicted_proba))

    queue = payload.get("queue")
    if isinstance(queue, str):
        ground_truth = map_queue_to_category(queue)
    else:
        ground_truth = None

    update_ticket(
        ticket_id=payload['ticket_id'],
        predicted_category=predicted_class,
        confidence=confidence,
        ground_truth_category=ground_truth
    )

    if predicted_class != ground_truth:
        logger.warning(
            f"Mismatch for ticket {payload['ticket_id']}: Predicted {predicted_class} vs GT {ground_truth}"
        )

    return {
        "ticket_id": payload['ticket_id'],
        "predicted_category": predicted_class,
        "confidence": confidence,
        "ground_truth_category": ground_truth
    }
