from typing import Optional, Any

from pydantic import BaseModel

from datetime import datetime


class TicketRequest(BaseModel):
    subject: str
    body: str
    priority: str = "Medium"


class ProcessTicketsRequest(BaseModel):
    batch_size: int = 100
    priority_filter: Optional[str] = None


class TaskStatusResponse(BaseModel):
    status: str
    task_id: str
    message: Optional[str]
    result: Optional[Any] = None
    error: Optional[str] = None


class TicketResponse(BaseModel):
    ticket_id: int
    subject: Optional[str]
    body: Optional[str]
    answer: Optional[str]
    type: Optional[str]
    queue: Optional[str]
    priority: Optional[str]
    language: Optional[str]
    tags: Optional[Any]
    predicted_category: Optional[str]
    confidence: Optional[float]
    summary: Optional[str]
    processed_at: Optional[datetime]
    ground_truth_category: Optional[str]

    class Config:
        orm_mode = True
