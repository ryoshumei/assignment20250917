import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_run_detail_contract(client):
    """Contract test for GET /runs/{run_id} - NEW ENDPOINT"""
    # First create a workflow and run it
    create_response = client.post("/workflows", json={"name": "Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Add nodes
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "extract_text",
        "config": {}
    })
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "formatter",
        "config": {}
    })

    # Run the workflow
    client.post(f"/workflows/{workflow_id}/run")

    # Get the run ID from the runs list
    runs_response = client.get(f"/workflows/{workflow_id}/runs")
    runs_data = runs_response.json()
    assert len(runs_data["runs"]) > 0
    run_id = runs_data["runs"][0]["id"]

    # Test getting run details
    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    data = response.json()

    # Verify response schema matches OpenAPI spec
    assert "run" in data
    assert "steps" in data

    # Verify run object structure
    run = data["run"]
    assert "id" in run
    assert "workflow_id" in run
    assert "status" in run
    assert "started_at" in run
    assert run["id"] == run_id
    assert run["workflow_id"] == workflow_id

    # Verify steps array structure
    steps = data["steps"]
    assert isinstance(steps, list)

    if len(steps) > 0:
        step = steps[0]
        assert "id" in step
        assert "run_id" in step
        assert "node_type" in step
        assert "status" in step
        assert "started_at" in step
        assert step["run_id"] == run_id
        assert step["node_type"] in ["extract_text", "generative_ai", "formatter"]
        assert step["status"] in ["Pending", "Running", "Succeeded", "Failed"]

        # Optional fields
        if "node_id" in step:
            assert step["node_id"] is None or isinstance(step["node_id"], str)
        if "finished_at" in step:
            assert step["finished_at"] is None or isinstance(step["finished_at"], str)
        if "input_text" in step:
            assert step["input_text"] is None or isinstance(step["input_text"], str)
        if "output_text" in step:
            assert step["output_text"] is None or isinstance(step["output_text"], str)
        if "error_message" in step:
            assert step["error_message"] is None or isinstance(step["error_message"], str)


def test_get_nonexistent_run_detail_contract(client):
    """Contract test for GET /runs/{run_id} - run not found"""
    response = client.get("/runs/nonexistent-run-id")
    assert response.status_code == 404