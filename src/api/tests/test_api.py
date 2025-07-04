import pytest
from unittest.mock import patch
from datetime import datetime


@pytest.mark.asyncio
async def test_process_ticket_success(async_client, mock_celery):
    payload = {
        "subject": "Hello",
        "body": "This is a body",
        "priority": "High"
    }

    response = await async_client.post("/requests", json=payload)
    assert response.status_code == 201

    data = response.json()
    print(data)
    assert data["task_id"] == "mocked_task_id"
    assert data["status"] == "Task submitted"
    assert data["message"] == "New ticket will be processed"

    mock_celery["send_task"].assert_called_once()


@pytest.mark.asyncio
async def test_get_ticket_by_id_success(async_client):
    fake_ticket = {
        "ticket_id": 123,
        "subject": "Test subject",
        "body": "Test body",
        "answer": "Test answer",
        "type": "question",
        "queue": "general",
        "priority": "High",
        "language": "en",
        "tags": {"product": "laptop"},
        "predicted_category": "technical",
        "confidence": 0.95,
        "summary": "Short summary",
        "processed_at": datetime.utcnow(),
        "ground_truth_category": "technical"
    }

    with patch("app.database.fetch_record", return_value=fake_ticket) as mock_fetch:
        response = await async_client.get("/requests/123")

        assert response.status_code == 200
        data = response.json()
        assert data["ticket_id"] == 123
        assert data["subject"] == "Test subject"

        mock_fetch.assert_called_once_with("123")
