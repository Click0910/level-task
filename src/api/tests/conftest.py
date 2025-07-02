import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock


@pytest.fixture(scope="module")
def client():
    # Mock de todo el sistema Celery
    with patch("main.tasks") as mock_celery:
        # Configurar mocks para send_task y AsyncResult
        mock_task = Mock(id="mocked_task_id")
        mock_celery.send_task.return_value = mock_task

        # Mock de AsyncResult
        mock_async_result = Mock()
        mock_async_result.status = "SUCCESS"
        mock_async_result.ready.return_value = True
        mock_async_result.failed.return_value = False
        mock_celery.AsyncResult.return_value = mock_async_result

        from main import app
        yield TestClient(app)
