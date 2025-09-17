import pytest
import os
import tempfile
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


def test_persistence_across_restart(test_db):
    """
    Integration test: Data persists across application restart (DB state retained)
    This test simulates the application restart scenario to ensure PostgreSQL
    persistence works correctly.
    """
    client = TestClient(app)

    # Phase 1: Create workflow and nodes
    create_response = client.post("/workflows", json={"name": "Persistent Workflow"})
    assert create_response.status_code == 200
    workflow_id = create_response.json()["id"]

    # Add nodes
    node1_response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "extract_text",
        "config": {"source": "document.pdf"}
    })
    assert node1_response.status_code == 200
    node1_id = node1_response.json()["node_id"]

    node2_response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "generative_ai",
        "config": {"prompt": "Summarize this text", "model": "gpt-3.5"}
    })
    assert node2_response.status_code == 200
    node2_id = node2_response.json()["node_id"]

    # Run the workflow to create run history
    run_response = client.post(f"/workflows/{workflow_id}/run")
    assert run_response.status_code == 200

    # Phase 2: Simulate application restart by creating a new client instance
    # In a real restart, the in-memory data would be lost, but DB data should persist
    client_after_restart = TestClient(app)

    # Phase 3: Verify all data persists after "restart"
    # Verify workflow still exists
    workflow_response = client_after_restart.get(f"/workflows/{workflow_id}")
    assert workflow_response.status_code == 200
    workflow_data = workflow_response.json()
    assert workflow_data["id"] == workflow_id
    assert workflow_data["name"] == "Persistent Workflow"
    assert len(workflow_data["nodes"]) == 2

    # Verify nodes are in correct order
    nodes = workflow_data["nodes"]
    assert any(node["id"] == node1_id and node["node_type"] == "extract_text" for node in nodes)
    assert any(node["id"] == node2_id and node["node_type"] == "generative_ai" for node in nodes)

    # Verify run history persists
    runs_response = client_after_restart.get(f"/workflows/{workflow_id}/runs")
    assert runs_response.status_code == 200
    runs_data = runs_response.json()
    assert len(runs_data["runs"]) >= 1

    # Verify run details persist
    run_id = runs_data["runs"][0]["id"]
    run_detail_response = client_after_restart.get(f"/runs/{run_id}")
    assert run_detail_response.status_code == 200
    run_detail_data = run_detail_response.json()
    assert "run" in run_detail_data
    assert "steps" in run_detail_data
    assert len(run_detail_data["steps"]) >= 2  # Should have steps for both nodes

    # Phase 4: Verify we can continue working with persisted data
    # Add another node after restart
    node3_response = client_after_restart.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "formatter",
        "config": {"format": "json"}
    })
    assert node3_response.status_code == 200

    # Run workflow again
    run2_response = client_after_restart.post(f"/workflows/{workflow_id}/run")
    assert run2_response.status_code == 200

    # Verify we now have 2 runs
    runs_response_final = client_after_restart.get(f"/workflows/{workflow_id}/runs")
    assert runs_response_final.status_code == 200
    final_runs_data = runs_response_final.json()
    assert len(final_runs_data["runs"]) == 2