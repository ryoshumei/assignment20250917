import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_workflow_contract(client):
    """Contract test for GET /workflows/{id}"""
    # First create a workflow
    create_response = client.post("/workflows", json={"name": "Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Add a node to verify nodes array in response
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "extract_text",
        "config": {"test": "config"}
    })

    # Test GET workflow
    response = client.get(f"/workflows/{workflow_id}")

    assert response.status_code == 200
    data = response.json()

    # Verify response schema matches OpenAPI spec
    assert "id" in data
    assert "name" in data
    assert "nodes" in data
    assert data["id"] == workflow_id
    assert data["name"] == "Test Workflow"
    assert isinstance(data["nodes"], list)
    assert len(data["nodes"]) >= 1  # We added one node

    # Verify node structure
    node = data["nodes"][0]
    assert "id" in node
    assert "node_type" in node
    assert "config" in node


def test_get_workflow_not_found_contract(client):
    """Contract test for GET /workflows/{id} - not found case"""
    response = client.get("/workflows/nonexistent-id")
    assert response.status_code == 404