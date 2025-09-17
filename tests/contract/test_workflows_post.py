import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_create_workflow_contract(client):
    """Contract test for POST /workflows"""
    request_data = {"name": "Test Workflow"}

    response = client.post("/workflows", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # Verify response schema matches OpenAPI spec
    assert "id" in data
    assert "name" in data
    assert data["name"] == "Test Workflow"
    assert isinstance(data["id"], str)
    assert len(data["id"]) > 0  # UUID should be non-empty string