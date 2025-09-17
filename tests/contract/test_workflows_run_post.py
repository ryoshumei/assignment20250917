import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_run_workflow_contract(client):
    """Contract test for POST /workflows/{id}/run"""
    # First create a workflow
    create_response = client.post("/workflows", json={"name": "Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Add nodes to the workflow
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "extract_text",
        "config": {}
    })
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "formatter",
        "config": {}
    })

    # Test running the workflow
    response = client.post(f"/workflows/{workflow_id}/run")

    assert response.status_code == 200
    data = response.json()

    # Verify response schema matches OpenAPI spec
    assert "final_output" in data
    assert isinstance(data["final_output"], str)


def test_run_nonexistent_workflow_contract(client):
    """Contract test for POST /workflows/{id}/run - workflow not found"""
    response = client.post("/workflows/nonexistent-id/run")
    assert response.status_code == 404