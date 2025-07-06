import os
import json
from typing import Any, Dict, List

from celery import Celery
from celery.utils.log import get_logger

from app.database import (
    fetch_unprocessed_tickets,
    save_new_ticket,
)
from scripts import seed


BROKER_URL = os.getenv("BROKER_URL")
REDIS_URL = os.getenv("REDIS_URL")


logger = get_logger(__name__)
ticket = Celery(
    "ticket_worker",
    broker=BROKER_URL,
    backend=REDIS_URL,
)


@ticket.task(bind=True, name="process_new_ticket", acks_late=True, queue="ticket_queue")
def process_new_ticket(self, **kwargs):
    """
    Insert new ticket in the DB and launch inference.
    """
    logger.info("🚀 Recibido nuevo ticket")
    self.update_state(state="STARTED", meta={"stage": "saving"})

    try:
        ticket_data = save_new_ticket(kwargs)

        payload = {
            "ticket_id": ticket_data["ticket_id"],
            "subject": ticket_data["subject"],
            "body": ticket_data["body"],
            "queue": ticket_data.get("queue", ""),
        }

        ticket.send_task(
            "run_inference",
            kwargs=payload,
            queue="inference_queue"
        )

        return {
            "message": "Ticket saved and inference started",
            "ticket_id": ticket_data["ticket_id"]
        }

    except Exception as e:
        logger.error(f"❌ Error saving new ticket: {str(e)}")
        raise self.retry(exc=e, countdown=5, max_retries=3)


@ticket.task(bind=True, name="seed_database", acks_late=True, queue="ticket_queue")
def upload_data_to_db(self, batch_size=1000):

    seed.seed_database(batch_size=batch_size)


@ticket.task(bind=True, name="process_existing_ticket", acks_late=True, queue="ticket_queue")
def process_existing_data(self, batch_size=1000):
    # 1. Get nor processed tickets
    tickets = fetch_unprocessed_tickets()
    logger.info(tickets)

    # 2. Process each ticket with validation
    for ticket_data in tickets:
        try:

            # Payload for inference
            payload = {
                "ticket_id": ticket_data.get("ticket_id"),
                "subject": ticket_data.get("subject"),
                "body": ticket_data.get("body"),
                "queue": ticket_data.get("queue"),
            }

            # 3. Send to queue for inference
            ticket.send_task(
                'run_inference',
                kwargs=payload,
                queue='inference_queue',
            )

        except ValidationError as e:
            logger.error(f"Invalid ticket data: {ticket_data}. Error: {e}")
