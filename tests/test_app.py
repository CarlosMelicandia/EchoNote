import json
import pytest
from unittest.mock import patch
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_save_task_monkeypatch(client):
    # This mock will replace the real `create_task` during the test
    with patch('app.create_task') as mock_create_task:
        mock_create_task.return_value = None  # You can set return behavior if needed

        # Call the endpoint
        response = client.post('/api/save_task',
            data=json.dumps({"tasks": [{"text": "Fake DB task"}]}),
            content_type='application/json'
        )

        # Assertions
        assert response.status_code == 200
        assert b"1 tasks saved" in response.data

        # Make sure mock was called correctly
        mock_create_task.assert_called_once_with("Fake DB task")
