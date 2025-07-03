import os

from celery import Celery, shared_task
from celery.result import AsyncResult
from fastapi import FastAPI, Body, Query, HTTPException

from app import models
from app import database
from typing import Optional, Any, List
from utils.responses import build_response


app = FastAPI()
tasks = Celery(
    "tickets",
    broker=os.getenv("BROKER_URL"),
    backend=os.getenv("REDIS_URL"),
)


@app.post("/requests", status_code=201, response_model=models.TaskStatusResponse)
async def process_ticket(data: models.TicketRequest):
    """
    Crea un nuevo ticket y lanza inferencia en background.
    """
    try:
        task = tasks.send_task(
            "process_new_ticket",
            kwargs=data.dict(),
            queue="ticket_queue"
        )
        return build_response(task.id, "New ticket will be processed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/seed")
async def trigger_seed(batch_size: int = 1000):
    try:
        task = tasks.send_task(
            "seed_database",
            kwargs={"batch_size": batch_size},
            queue="ticket_queue"
        )
        return build_response(task.id, f"Seeding started with batch size: {batch_size}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-tickets", response_model=models.TaskStatusResponse)
async def process_data(requests: models.ProcessTicketsRequest):
    try:
        data = requests.model_dump()
        task = tasks.send_task(
            "process_existing_ticket",
            kwargs={"batch_size": data.get("batch_size")},
            queue="ticket_queue"
        )
        return build_response(
            task.id,
            f"Processing existing data {data.get('batch_size')}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/requests/{id}", response_model=models.TicketResponse)
async def get_record(id: str):
    try:
        ticket = database.fetch_record(id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return ticket
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/requests", response_model=List[models.TicketResponse])
async def get_requests_by_category(
        category: Optional[str] = Query(None, description="Category to filter by")
):
    try:
        if not category:
            raise HTTPException(
                status_code=422,
                detail="Query parameter 'category' is required"
            )

        filtered_tickets = database.filter_tickets_category(category)
        return filtered_tickets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    try:
        task_result = AsyncResult(task_id, app=tasks)

        match task_result.state:
            case "PENDING":
                return {"task_id": task_id, "status": "pending"}
            case "STARTED":
                return {"task_id": task_id, "status": "processing"}
            case "SUCCESS":
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "result": task_result.result
                }
            case "FAILURE":
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(task_result.result)
                }
            case _:
                raise HTTPException(status_code=500, detail="Unknown task state")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching task status: {str(e)}")
