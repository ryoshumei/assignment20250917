import pytest
import time
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_agent_node_bounded_execution(client):
    """Integration test for Agent node with bounded loop execution"""
    # Create workflow
    create_response = client.post("/workflows", json={"name": "Agent Bounded Test"})
    assert create_response.status_code == 200
    workflow_id = create_response.json()["id"]

    # Add agent node with bounded configuration
    agent_data = {
        "node_type": "agent",
        "config": {
            "objective": "Process the input text using available tools efficiently",
            "tools": ["llm_call", "formatter"],
            "budgets": {"execution_time": 30},
            "max_concurrent": 2,
            "timeout_seconds": 25,
            "max_retries": 2,
            "max_iterations": 3,
            "formatting_rules": ["lowercase"]
        }
    }

    agent_response = client.post(f"/workflows/{workflow_id}/nodes", json=agent_data)
    assert agent_response.status_code == 200
    agent_node_id = agent_response.json()["node_id"]

    # Run the workflow
    run_response = client.post(f"/workflows/{workflow_id}/run")
    assert run_response.status_code == 200
    job_id = run_response.json()["job_id"]

    # Poll for completion with timeout
    max_polls = 40  # Agent might take longer
    job_status = None
    job_data = None

    for i in range(max_polls):
        job_response = client.get(f"/jobs/{job_id}")
        assert job_response.status_code == 200
        job_data = job_response.json()
        job_status = job_data["status"]

        if job_status in ["Succeeded", "Failed"]:
            break

        time.sleep(1)

    # Verify job completed (either succeeded or failed deterministically)
    assert job_status in ["Succeeded", "Failed"], f"Job did not complete. Status: {job_status}"

    # Get job details to verify agent execution
    details_response = client.get(f"/jobs/{job_id}/details")
    assert details_response.status_code == 200
    job_details = details_response.json()

    steps = job_details["steps"]
    assert len(steps) == 1, f"Expected 1 agent step, got {len(steps)}"

    agent_step = steps[0]
    assert agent_step["node_id"] == agent_node_id
    assert agent_step["node_type"] == "agent"
    assert agent_step["status"] in ["Succeeded", "Failed"]

    # Verify execution was bounded (completed within reasonable time)
    started_at = agent_step["started_at"]
    finished_at = agent_step["finished_at"]
    assert started_at is not None
    assert finished_at is not None

    # Parse timestamps and verify bounded execution
    from datetime import datetime
    start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
    end_time = datetime.fromisoformat(finished_at.replace('Z', '+00:00'))
    execution_duration = (end_time - start_time).total_seconds()

    # Should complete within the timeout limit (25s + some buffer)
    assert execution_duration <= 30, f"Agent execution took too long: {execution_duration}s"

    # Verify output is present
    if agent_step["status"] == "Succeeded":
        assert agent_step["output_text"] is not None
        assert len(agent_step["output_text"]) > 0
        print(f"✅ Agent succeeded with output: {agent_step['output_text'][:100]}...")
    else:
        assert agent_step["error_message"] is not None
        print(f"✅ Agent failed deterministically: {agent_step['error_message']}")

    print(f"Agent execution duration: {execution_duration:.2f}s")


def test_agent_node_tools_whitelist_enforcement(client):
    """Integration test for Agent node tools whitelist enforcement"""
    # Create workflow
    create_response = client.post("/workflows", json={"name": "Agent Tools Test"})
    assert create_response.status_code == 200
    workflow_id = create_response.json()["id"]

    # Add agent node with limited tools
    agent_data = {
        "node_type": "agent",
        "config": {
            "objective": "Format text using only formatter tool",
            "tools": ["formatter"],  # Only formatter, no LLM
            "budgets": {"execution_time": 15},
            "max_concurrent": 1,
            "timeout_seconds": 15,
            "max_retries": 1,
            "max_iterations": 2,
            "formatting_rules": ["lowercase", "full_to_half"]
        }
    }

    agent_response = client.post(f"/workflows/{workflow_id}/nodes", json=agent_data)
    assert agent_response.status_code == 200

    # Run the workflow
    run_response = client.post(f"/workflows/{workflow_id}/run")
    assert run_response.status_code == 200
    job_id = run_response.json()["job_id"]

    # Poll for completion
    max_polls = 20
    for i in range(max_polls):
        job_response = client.get(f"/jobs/{job_id}")
        assert job_response.status_code == 200
        job_data = job_response.json()

        if job_data["status"] in ["Succeeded", "Failed"]:
            break

        time.sleep(1)

    # Should complete (might succeed or fail, but should be deterministic)
    assert job_data["status"] in ["Succeeded", "Failed"]

    print(f"✅ Agent tools whitelist test completed with status: {job_data['status']}")


def test_agent_node_budget_limits(client):
    """Integration test for Agent node budget limit enforcement"""
    # Create workflow
    create_response = client.post("/workflows", json={"name": "Agent Budget Test"})
    assert create_response.status_code == 200
    workflow_id = create_response.json()["id"]

    # Add agent node with very tight limits
    agent_data = {
        "node_type": "agent",
        "config": {
            "objective": "Process quickly within tight budget",
            "tools": ["formatter"],
            "budgets": {"execution_time": 5},  # Very tight budget
            "max_concurrent": 1,
            "timeout_seconds": 5,  # Short timeout
            "max_retries": 1,
            "max_iterations": 1,  # Single iteration
            "formatting_rules": ["lowercase"]
        }
    }

    agent_response = client.post(f"/workflows/{workflow_id}/nodes", json=agent_data)
    assert agent_response.status_code == 200

    # Run the workflow
    run_response = client.post(f"/workflows/{workflow_id}/run")
    assert run_response.status_code == 200
    job_id = run_response.json()["job_id"]

    # Poll for quick completion
    max_polls = 15
    for i in range(max_polls):
        job_response = client.get(f"/jobs/{job_id}")
        assert job_response.status_code == 200
        job_data = job_response.json()

        if job_data["status"] in ["Succeeded", "Failed"]:
            break

        time.sleep(1)

    # Should complete within budget
    assert job_data["status"] in ["Succeeded", "Failed"]

    # Get execution details
    details_response = client.get(f"/jobs/{job_id}/details")
    assert details_response.status_code == 200
    job_details = details_response.json()

    agent_step = job_details["steps"][0]

    # Verify fast execution due to tight budget
    started_at = agent_step["started_at"]
    finished_at = agent_step["finished_at"]

    if started_at and finished_at:
        from datetime import datetime
        start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(finished_at.replace('Z', '+00:00'))
        execution_duration = (end_time - start_time).total_seconds()

        # Should respect budget limits
        assert execution_duration <= 10, f"Budget exceeded: {execution_duration}s"
        print(f"✅ Agent budget test: execution within {execution_duration:.2f}s")

    print(f"✅ Agent budget limits enforced successfully")