from typing import Optional, Any

from pydantic import BaseModel


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
