import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_add_node_contract(client):
    """Contract test for POST /workflows/{id}/nodes"""
    # First create a workflow
    create_response = client.post("/workflows", json={"name": "Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Test adding a node
    node_data = {
        "node_type": "generative_ai",
        "config": {"prompt": "Test prompt: {text}", "model": "gpt-4.1-mini"}
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json=node_data)

    assert response.status_code == 200
    data = response.json()

    # Verify response schema matches OpenAPI spec
    assert "message" in data
    assert "node_id" in data
    assert isinstance(data["node_id"], str)
    assert len(data["node_id"]) > 0  # UUID should be non-empty string


def test_add_node_to_nonexistent_workflow_contract(client):
    """Contract test for POST /workflows/{id}/nodes - workflow not found"""
    node_data = {
        "node_type": "extract_text",
        "config": {"test": "config"}
    }

    response = client.post("/workflows/nonexistent-id/nodes", json=node_data)
    assert response.status_code == 404