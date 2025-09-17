import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_job_contract(client):
    """Contract test for GET /jobs/{job_id} - NEW ENDPOINT"""
    # First create a workflow and run it to get a job_id
    create_response = client.post("/workflows", json={"name": "Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Add a node
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "extract_text",
        "config": {}
    })

    # Run the workflow to create a job
    run_response = client.post(f"/workflows/{workflow_id}/run")
    job_id = run_response.json()["job_id"]

    # Test getting the job status
    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()

    # Verify response schema matches OpenAPI spec
    required_fields = ["id", "workflow_id", "status", "started_at"]
    for field in required_fields:
        assert field in data
        assert data[field] is not None

    assert data["id"] == job_id
    assert data["workflow_id"] == workflow_id
    assert data["status"] in ["Pending", "Running", "Succeeded", "Failed"]
    assert isinstance(data["started_at"], str)

    # Optional fields
    optional_fields = ["finished_at", "error_message", "final_output"]
    for field in optional_fields:
        if field in data and data[field] is not None:
            assert isinstance(data[field], str)


def test_get_nonexistent_job_contract(client):
    """Contract test for GET /jobs/{job_id} - job not found"""
    response = client.get("/jobs/nonexistent-job-id")
    assert response.status_code == 404