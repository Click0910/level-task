import pytest
import pytest_asyncio
from unittest.mock import patch, Mock
from httpx import AsyncClient
from main import app


@pytest.fixture
def mock_celery():
    """
    Mocks de send_task y AsyncResult dentro de app.main
    """
    with patch("main.tasks.send_task") as mock_send_task, \
         patch("main.AsyncResult") as mock_async_result:

        # Simular un task Celery
        mock_task = Mock()
        mock_task.id = "mocked_task_id"
        mock_send_task.return_value = mock_task

        # Simular una respuesta de AsyncResult si lo usas
        result = Mock()
        result.status = "SUCCESS"
        result.ready.return_value = True
        result.failed.return_value = False
        mock_async_result.return_value = result

        yield {
            "send_task": mock_send_task,
            "async_result": mock_async_result
        }


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
