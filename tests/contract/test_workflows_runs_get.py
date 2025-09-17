import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_workflow_runs_contract(client):
    """Contract test for GET /workflows/{id}/runs - NEW ENDPOINT"""
    # First create a workflow
    create_response = client.post("/workflows", json={"name": "Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Add a node
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "extract_text",
        "config": {}
    })

    # Run the workflow to create a run record
    client.post(f"/workflows/{workflow_id}/run")

    # Test getting runs for the workflow
    response = client.get(f"/workflows/{workflow_id}/runs")

    assert response.status_code == 200
    data = response.json()

    # Verify response schema matches OpenAPI spec
    assert "runs" in data
    assert isinstance(data["runs"], list)

    if len(data["runs"]) > 0:
        run = data["runs"][0]
        assert "id" in run
        assert "workflow_id" in run
        assert "status" in run
        assert "started_at" in run
        assert run["workflow_id"] == workflow_id
        assert run["status"] in ["Pending", "Running", "Succeeded", "Failed"]

        # For async jobs, we expect job_id field
        if "job_id" in run:
            assert isinstance(run["job_id"], str)

        # Optional fields
        if "finished_at" in run:
            assert run["finished_at"] is None or isinstance(run["finished_at"], str)
        if "error_message" in run:
            assert run["error_message"] is None or isinstance(run["error_message"], str)
        if "final_output" in run:
            assert run["final_output"] is None or isinstance(run["final_output"], str)


def test_get_runs_for_nonexistent_workflow_contract(client):
    """Contract test for GET /workflows/{id}/runs - workflow not found"""
    response = client.get("/workflows/nonexistent-id/runs")
    assert response.status_code == 404