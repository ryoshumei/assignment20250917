import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_add_edge_contract(client):
    """Contract test for POST /workflows/{id}/edges"""
    # First create a workflow
    create_response = client.post("/workflows", json={"name": "Test DAG Workflow"})
    workflow_id = create_response.json()["id"]

    # Add two nodes to connect
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

    # Test adding an edge
    edge_data = {
        "from_node_id": node1_id,
        "to_node_id": node2_id
    }

    response = client.post(f"/workflows/{workflow_id}/edges", json=edge_data)

    assert response.status_code == 200
    data = response.json()

    # Verify response schema matches OpenAPI spec
    assert "message" in data
    assert "edge_id" in data
    assert isinstance(data["edge_id"], str)
    assert len(data["edge_id"]) > 0  # UUID should be non-empty string


def test_add_edge_with_cycle_detection_contract(client):
    """Contract test for POST /workflows/{id}/edges - cycle detection"""
    # Create workflow and nodes
    create_response = client.post("/workflows", json={"name": "Test Cycle Workflow"})
    workflow_id = create_response.json()["id"]

    node1_data = {
        "node_type": "generative_ai",
        "config": {"prompt": "Process: {text}", "model": "gpt-4.1-mini"}
    }
    node1_response = client.post(f"/workflows/{workflow_id}/nodes", json=node1_data)
    node1_id = node1_response.json()["node_id"]

    node2_data = {
        "node_type": "formatter",
        "config": {"rules": ["lowercase"]}
    }
    node2_response = client.post(f"/workflows/{workflow_id}/nodes", json=node2_data)
    node2_id = node2_response.json()["node_id"]

    # Add first edge
    edge1_data = {"from_node_id": node1_id, "to_node_id": node2_id}
    response1 = client.post(f"/workflows/{workflow_id}/edges", json=edge1_data)
    assert response1.status_code == 200

    # Try to add reverse edge (should create cycle and fail)
    edge2_data = {"from_node_id": node2_id, "to_node_id": node1_id}
    response2 = client.post(f"/workflows/{workflow_id}/edges", json=edge2_data)

    assert response2.status_code == 400
    assert "cycle" in response2.json()["detail"].lower()


def test_add_edge_invalid_node_refs_contract(client):
    """Contract test for POST /workflows/{id}/edges - invalid node references"""
    # Create workflow
    create_response = client.post("/workflows", json={"name": "Test Invalid Refs"})
    workflow_id = create_response.json()["id"]

    # Try to add edge with nonexistent node IDs
    edge_data = {
        "from_node_id": "nonexistent-node-1",
        "to_node_id": "nonexistent-node-2"
    }

    response = client.post(f"/workflows/{workflow_id}/edges", json=edge_data)
    assert response.status_code == 400


def test_add_edge_to_nonexistent_workflow_contract(client):
    """Contract test for POST /workflows/{id}/edges - workflow not found"""
    edge_data = {
        "from_node_id": "some-node-id",
        "to_node_id": "another-node-id"
    }

    response = client.post("/workflows/nonexistent-id/edges", json=edge_data)
    assert response.status_code == 404