import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_edges_contract(client):
    """Contract test for GET /workflows/{id}/edges"""
    # Create workflow
    create_response = client.post("/workflows", json={"name": "Test DAG Workflow"})
    workflow_id = create_response.json()["id"]

    # Add two nodes
    node1_data = {
        "node_type": "generative_ai",
        "config": {"prompt": "Process this: {text}", "model": "gpt-4.1-mini"}
    }
    node1_response = client.post(f"/workflows/{workflow_id}/nodes", json=node1_data)
    node1_id = node1_response.json()["node_id"]

    node2_data = {
        "node_type": "formatter",
        "config": {"rules": ["lowercase"]}
    }
    node2_response = client.post(f"/workflows/{workflow_id}/nodes", json=node2_data)
    node2_id = node2_response.json()["node_id"]

    # Add an edge
    edge_data = {
        "from_node_id": node1_id,
        "to_node_id": node2_id,
        "from_port": "output",
        "to_port": "input"
    }
    edge_response = client.post(f"/workflows/{workflow_id}/edges", json=edge_data)
    edge_id = edge_response.json()["edge_id"]

    # Test getting edges
    response = client.get(f"/workflows/{workflow_id}/edges")

    assert response.status_code == 200
    data = response.json()

    # Verify response schema matches OpenAPI spec
    assert "edges" in data
    assert isinstance(data["edges"], list)
    assert len(data["edges"]) == 1

    edge = data["edges"][0]
    assert "id" in edge
    assert "workflow_id" in edge
    assert "from_node_id" in edge
    assert "from_port" in edge
    assert "to_node_id" in edge
    assert "to_port" in edge
    assert "condition" in edge

    # Verify edge data
    assert edge["id"] == edge_id
    assert edge["workflow_id"] == workflow_id
    assert edge["from_node_id"] == node1_id
    assert edge["to_node_id"] == node2_id
    assert edge["from_port"] == "output"
    assert edge["to_port"] == "input"


def test_get_edges_empty_workflow_contract(client):
    """Contract test for GET /workflows/{id}/edges - empty workflow"""
    # Create workflow with no edges
    create_response = client.post("/workflows", json={"name": "Empty Workflow"})
    workflow_id = create_response.json()["id"]

    # Test getting edges
    response = client.get(f"/workflows/{workflow_id}/edges")

    assert response.status_code == 200
    data = response.json()

    # Should return empty list
    assert "edges" in data
    assert isinstance(data["edges"], list)
    assert len(data["edges"]) == 0


def test_get_edges_nonexistent_workflow_contract(client):
    """Contract test for GET /workflows/{id}/edges - workflow not found"""
    response = client.get("/workflows/nonexistent-id/edges")
    assert response.status_code == 404