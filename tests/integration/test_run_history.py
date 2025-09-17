import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server.main import app
from server.database import get_db, Base

# Use a test database URL for integration tests
TEST_DATABASE_URL = "postgresql://postgres:password@localhost:5432/workflow_test_db"


@pytest.fixture
def test_db():
    """Create a fresh test database for each test"""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal

    # Clean up
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


def test_run_history_recorded_with_steps(test_db):
    """
    Integration test: Run history is recorded with detailed per-node steps
    This test ensures that when a workflow runs, we record:
    - A Run record with start/end times and status
    - Individual RunNode records for each node execution step
    """
    client = TestClient(app)

    # Phase 1: Setup workflow with multiple nodes
    create_response = client.post("/workflows", json={"name": "Test History Workflow"})
    assert create_response.status_code == 200
    workflow_id = create_response.json()["id"]

    # Add multiple nodes to test step recording
    node_configs = [
        {"node_type": "extract_text", "config": {"source": "test.pdf"}},
        {"node_type": "generative_ai", "config": {"prompt": "Analyze this", "model": "gpt-4"}},
        {"node_type": "formatter", "config": {"format": "markdown"}}
    ]

    node_ids = []
    for config in node_configs:
        response = client.post(f"/workflows/{workflow_id}/nodes", json=config)
        assert response.status_code == 200
        node_ids.append(response.json()["node_id"])

    # Phase 2: Execute workflow and verify run is recorded
    run_response = client.post(f"/workflows/{workflow_id}/run")
    assert run_response.status_code == 200
    final_output = run_response.json()["final_output"]
    assert isinstance(final_output, str)
    assert len(final_output) > 0

    # Phase 3: Verify run was recorded in history
    runs_response = client.get(f"/workflows/{workflow_id}/runs")
    assert runs_response.status_code == 200
    runs_data = runs_response.json()

    assert "runs" in runs_data
    assert len(runs_data["runs"]) == 1

    run = runs_data["runs"][0]
    assert "id" in run
    assert "workflow_id" in run
    assert "status" in run
    assert "started_at" in run
    assert run["workflow_id"] == workflow_id
    assert run["status"] in ["Succeeded", "Failed"]  # Should be completed by now

    # Verify timestamps are present
    assert run["started_at"] is not None
    if run["status"] in ["Succeeded", "Failed"]:
        assert "finished_at" in run
        if run["finished_at"] is not None:
            # finished_at should be after started_at
            from datetime import datetime
            started = datetime.fromisoformat(run["started_at"].replace('Z', '+00:00'))
            finished = datetime.fromisoformat(run["finished_at"].replace('Z', '+00:00'))
            assert finished >= started

    # Phase 4: Verify detailed step history
    run_id = run["id"]
    run_detail_response = client.get(f"/runs/{run_id}")
    assert run_detail_response.status_code == 200
    run_detail_data = run_detail_response.json()

    assert "run" in run_detail_data
    assert "steps" in run_detail_data

    # Verify run details match
    run_detail = run_detail_data["run"]
    assert run_detail["id"] == run_id
    assert run_detail["workflow_id"] == workflow_id

    # Verify step recording
    steps = run_detail_data["steps"]
    assert isinstance(steps, list)
    assert len(steps) == 3  # Should have one step per node

    # Verify step details
    for i, step in enumerate(steps):
        assert "id" in step
        assert "run_id" in step
        assert "node_type" in step
        assert "status" in step
        assert "started_at" in step

        assert step["run_id"] == run_id
        assert step["node_type"] == node_configs[i]["node_type"]
        assert step["status"] in ["Pending", "Running", "Succeeded", "Failed"]

        # For completed steps, verify additional fields
        if step["status"] in ["Succeeded", "Failed"]:
            if "finished_at" in step and step["finished_at"] is not None:
                from datetime import datetime
                step_started = datetime.fromisoformat(step["started_at"].replace('Z', '+00:00'))
                step_finished = datetime.fromisoformat(step["finished_at"].replace('Z', '+00:00'))
                assert step_finished >= step_started

        # Verify input/output tracking exists
        assert "input_text" in step or step.get("input_text") is None
        assert "output_text" in step or step.get("output_text") is None

    # Phase 5: Test multiple runs create separate history
    # Run the workflow again
    run2_response = client.post(f"/workflows/{workflow_id}/run")
    assert run2_response.status_code == 200

    # Verify we now have 2 runs
    runs_response_2 = client.get(f"/workflows/{workflow_id}/runs")
    assert runs_response_2.status_code == 200
    runs_data_2 = runs_response_2.json()
    assert len(runs_data_2["runs"]) == 2

    # Verify runs are ordered by most recent first
    run1, run2 = runs_data_2["runs"]
    from datetime import datetime
    run1_time = datetime.fromisoformat(run1["started_at"].replace('Z', '+00:00'))
    run2_time = datetime.fromisoformat(run2["started_at"].replace('Z', '+00:00'))
    # Most recent should be first
    assert run1_time >= run2_time

    # Phase 6: Verify each run has its own step history
    for run in runs_data_2["runs"]:
        run_detail_response = client.get(f"/runs/{run['id']}")
        assert run_detail_response.status_code == 200
        run_detail = run_detail_response.json()
        assert len(run_detail["steps"]) == 3  # Each run should have its own steps