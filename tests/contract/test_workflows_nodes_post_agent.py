import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_add_agent_node_valid_config_contract(client):
    """Contract test for POST /workflows/{id}/nodes - valid agent config"""
    # Create workflow
    create_response = client.post("/workflows", json={"name": "Agent Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Test adding valid agent node
    agent_data = {
        "node_type": "agent",
        "config": {
            "objective": "Process and format text using available tools",
            "tools": ["llm_call", "formatter"],
            "budgets": {"execution_time": 30},
            "max_concurrent": 2,
            "timeout_seconds": 25,
            "max_retries": 2,
            "max_iterations": 3,
            "formatting_rules": ["lowercase"]
        }
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json=agent_data)

    assert response.status_code == 200
    data = response.json()

    # Verify response schema
    assert "message" in data
    assert "node_id" in data
    assert isinstance(data["node_id"], str)
    assert len(data["node_id"]) > 0


def test_add_agent_node_missing_objective_contract(client):
    """Contract test for POST /workflows/{id}/nodes - agent missing objective"""
    create_response = client.post("/workflows", json={"name": "Agent Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Test agent without objective
    agent_data = {
        "node_type": "agent",
        "config": {
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30}
        }
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json=agent_data)
    assert response.status_code == 400
    assert "objective" in response.json()["detail"]


def test_add_agent_node_missing_tools_contract(client):
    """Contract test for POST /workflows/{id}/nodes - agent missing tools"""
    create_response = client.post("/workflows", json={"name": "Agent Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Test agent without tools
    agent_data = {
        "node_type": "agent",
        "config": {
            "objective": "Process text",
            "budgets": {"execution_time": 30}
        }
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json=agent_data)
    assert response.status_code == 400
    assert "tools" in response.json()["detail"]


def test_add_agent_node_invalid_tools_contract(client):
    """Contract test for POST /workflows/{id}/nodes - agent invalid tools"""
    create_response = client.post("/workflows", json={"name": "Agent Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Test agent with invalid tools
    agent_data = {
        "node_type": "agent",
        "config": {
            "objective": "Process text",
            "tools": ["invalid_tool", "another_invalid"],
            "budgets": {"execution_time": 30}
        }
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json=agent_data)
    assert response.status_code == 400
    assert "invalid tool" in response.json()["detail"].lower()


def test_add_agent_node_missing_budgets_contract(client):
    """Contract test for POST /workflows/{id}/nodes - agent missing budgets"""
    create_response = client.post("/workflows", json={"name": "Agent Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Test agent without budgets
    agent_data = {
        "node_type": "agent",
        "config": {
            "objective": "Process text",
            "tools": ["llm_call"]
        }
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json=agent_data)
    assert response.status_code == 400
    assert "budgets" in response.json()["detail"]


def test_add_agent_node_excessive_concurrency_contract(client):
    """Contract test for POST /workflows/{id}/nodes - agent excessive concurrency"""
    create_response = client.post("/workflows", json={"name": "Agent Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Test agent with concurrency > 10
    agent_data = {
        "node_type": "agent",
        "config": {
            "objective": "Process text",
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30},
            "max_concurrent": 15  # > 10 limit
        }
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json=agent_data)
    assert response.status_code == 400
    assert "max_concurrent" in response.json()["detail"]


def test_add_agent_node_excessive_timeout_contract(client):
    """Contract test for POST /workflows/{id}/nodes - agent excessive timeout"""
    create_response = client.post("/workflows", json={"name": "Agent Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Test agent with timeout > 30s
    agent_data = {
        "node_type": "agent",
        "config": {
            "objective": "Process text",
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30},
            "timeout_seconds": 45  # > 30s limit
        }
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json=agent_data)
    assert response.status_code == 400
    assert "timeout_seconds" in response.json()["detail"]


def test_add_agent_node_excessive_retries_contract(client):
    """Contract test for POST /workflows/{id}/nodes - agent excessive retries"""
    create_response = client.post("/workflows", json={"name": "Agent Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Test agent with retries > 3
    agent_data = {
        "node_type": "agent",
        "config": {
            "objective": "Process text",
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30},
            "max_retries": 5  # > 3 limit
        }
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json=agent_data)
    assert response.status_code == 400
    assert "max_retries" in response.json()["detail"]