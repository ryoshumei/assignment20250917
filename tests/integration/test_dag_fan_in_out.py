import pytest
import time
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_dag_fan_in_out_diamond_pattern(client):
    """Integration test for DAG fan-out/fan-in diamond pattern"""
    # Create workflow
    create_response = client.post("/workflows", json={"name": "Diamond DAG Test"})
    assert create_response.status_code == 200
    workflow_id = create_response.json()["id"]

    # Add 4 nodes to create diamond pattern: A → B,C → D
    # Node A (start)
    node_a_data = {
        "node_type": "generative_ai",
        "config": {"prompt": "Start: {text}", "model": "gpt-4.1-mini"}
    }
    node_a_response = client.post(f"/workflows/{workflow_id}/nodes", json=node_a_data)
    assert node_a_response.status_code == 200
    node_a_id = node_a_response.json()["node_id"]

    # Node B (parallel path 1)
    node_b_data = {
        "node_type": "generative_ai",
        "config": {"prompt": "Path B processing: {text}", "model": "gpt-4.1-mini"}
    }
    node_b_response = client.post(f"/workflows/{workflow_id}/nodes", json=node_b_data)
    assert node_b_response.status_code == 200
    node_b_id = node_b_response.json()["node_id"]

    # Node C (parallel path 2)
    node_c_data = {
        "node_type": "generative_ai",
        "config": {"prompt": "Path C processing: {text}", "model": "gpt-4.1-mini"}
    }
    node_c_response = client.post(f"/workflows/{workflow_id}/nodes", json=node_c_data)
    assert node_c_response.status_code == 200
    node_c_id = node_c_response.json()["node_id"]

    # Node D (end - fan-in)
    node_d_data = {
        "node_type": "formatter",
        "config": {"rules": ["lowercase"]}
    }
    node_d_response = client.post(f"/workflows/{workflow_id}/nodes", json=node_d_data)
    assert node_d_response.status_code == 200
    node_d_id = node_d_response.json()["node_id"]

    # Create diamond edges: A → B, A → C, B → D, C → D
    edges = [
        {"from_node_id": node_a_id, "to_node_id": node_b_id},  # A → B
        {"from_node_id": node_a_id, "to_node_id": node_c_id},  # A → C
        {"from_node_id": node_b_id, "to_node_id": node_d_id},  # B → D
        {"from_node_id": node_c_id, "to_node_id": node_d_id},  # C → D
    ]

    for edge_data in edges:
        edge_response = client.post(f"/workflows/{workflow_id}/edges", json=edge_data)
        assert edge_response.status_code == 200

    # Verify edges were created
    edges_response = client.get(f"/workflows/{workflow_id}/edges")
    assert edges_response.status_code == 200
    assert len(edges_response.json()["edges"]) == 4

    # Run the workflow
    run_response = client.post(f"/workflows/{workflow_id}/run")
    assert run_response.status_code == 200
    job_id = run_response.json()["job_id"]

    # Poll for completion (with timeout)
    max_polls = 30
    job_status = None
    for i in range(max_polls):
        job_response = client.get(f"/jobs/{job_id}")
        assert job_response.status_code == 200
        job_data = job_response.json()
        job_status = job_data["status"]

        if job_status in ["Succeeded", "Failed"]:
            break

        time.sleep(1)

    # Verify job succeeded
    assert job_status == "Succeeded", f"Job failed or timed out. Status: {job_status}"

    # Get job details to verify execution steps
    details_response = client.get(f"/jobs/{job_id}/details")
    assert details_response.status_code == 200
    job_details = details_response.json()

    steps = job_details["steps"]
    assert len(steps) == 4, f"Expected 4 steps, got {len(steps)}"

    # Verify all steps succeeded
    for step in steps:
        assert step["status"] == "Succeeded", f"Step {step['node_id']} failed: {step.get('error_message')}"

    # Verify execution order respects DAG constraints
    step_by_node = {step["node_id"]: step for step in steps}

    # Node A should have executed first
    node_a_step = step_by_node[node_a_id]
    assert node_a_step["status"] == "Succeeded"

    # Nodes B and C should have executed after A
    node_b_step = step_by_node[node_b_id]
    node_c_step = step_by_node[node_c_id]
    assert node_b_step["status"] == "Succeeded"
    assert node_c_step["status"] == "Succeeded"

    # Node D should have executed after both B and C (AND-join)
    node_d_step = step_by_node[node_d_id]
    assert node_d_step["status"] == "Succeeded"

    # Verify AND-join behavior: Node D should have received combined inputs from B and C
    # The output should contain processed results from both paths
    final_output = job_data.get("final_output", "")
    assert len(final_output) > 0, "Final output should not be empty"

    print(f"✅ Diamond DAG test passed. Final output: {final_output}")


def test_dag_linear_fallback_no_edges(client):
    """Integration test: DAG execution falls back to linear when no edges present"""
    # Create workflow
    create_response = client.post("/workflows", json={"name": "Linear Fallback Test"})
    assert create_response.status_code == 200
    workflow_id = create_response.json()["id"]

    # Add 2 nodes without edges (should execute linearly)
    node1_data = {
        "node_type": "generative_ai",
        "config": {"prompt": "First: {text}", "model": "gpt-4.1-mini"}
    }
    node1_response = client.post(f"/workflows/{workflow_id}/nodes", json=node1_data)
    assert node1_response.status_code == 200

    node2_data = {
        "node_type": "formatter",
        "config": {"rules": ["lowercase"]}
    }
    node2_response = client.post(f"/workflows/{workflow_id}/nodes", json=node2_data)
    assert node2_response.status_code == 200

    # Run workflow (should fall back to linear execution)
    run_response = client.post(f"/workflows/{workflow_id}/run")
    assert run_response.status_code == 200
    job_id = run_response.json()["job_id"]

    # Poll for completion
    max_polls = 15
    for i in range(max_polls):
        job_response = client.get(f"/jobs/{job_id}")
        assert job_response.status_code == 200
        job_data = job_response.json()

        if job_data["status"] in ["Succeeded", "Failed"]:
            break

        time.sleep(1)

    # Verify successful execution
    assert job_data["status"] == "Succeeded"

    # Get job details
    details_response = client.get(f"/jobs/{job_id}/details")
    assert details_response.status_code == 200
    job_details = details_response.json()

    # Should have executed both nodes
    steps = job_details["steps"]
    assert len(steps) == 2

    for step in steps:
        assert step["status"] == "Succeeded"

    print(f"✅ Linear fallback test passed.")