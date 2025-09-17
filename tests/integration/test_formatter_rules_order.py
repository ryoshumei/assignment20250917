import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_formatter_rules_order_determinism(client):
    """Integration test: formatter rules order determinism"""
    # Create a workflow
    create_response = client.post("/workflows", json={"name": "Formatter Order Test"})
    workflow_id = create_response.json()["id"]

    # Test Case 1: lowercase then full_to_half
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "formatter",
        "config": {
            "rules": ["lowercase", "full_to_half"]
        }
    })

    run_response1 = client.post(f"/workflows/{workflow_id}/run")
    job_id1 = run_response1.json()["job_id"]

    # Wait for completion and get result
    import time
    time.sleep(2)
    job_response1 = client.get(f"/jobs/{job_id1}")
    result1 = job_response1.json().get("final_output", "")

    # Create second workflow for reverse order
    create_response2 = client.post("/workflows", json={"name": "Formatter Order Test 2"})
    workflow_id2 = create_response2.json()["id"]

    # Test Case 2: full_to_half then lowercase
    client.post(f"/workflows/{workflow_id2}/nodes", json={
        "node_type": "formatter",
        "config": {
            "rules": ["full_to_half", "lowercase"]
        }
    })

    run_response2 = client.post(f"/workflows/{workflow_id2}/run")
    job_id2 = run_response2.json()["job_id"]

    # Wait for completion and get result
    time.sleep(2)
    job_response2 = client.get(f"/jobs/{job_id2}")
    result2 = job_response2.json().get("final_output", "")

    # Both should produce the same result since they apply the same rules to the same input
    # The input starts as "Initial text from document" (default workflow starting text)
    # After lowercase + full_to_half: "initial text from document" (since the input is already half-width)
    expected_result = "initial text from document"
    assert result1.strip() == expected_result
    assert result2.strip() == expected_result
    assert result1 == result2  # Order shouldn't matter for these specific rules on this input


def test_formatter_rules_order_matters(client):
    """Integration test: cases where formatter rule order matters"""
    # Create workflow for testing order dependency
    create_response = client.post("/workflows", json={"name": "Order Dependency Test"})
    workflow_id = create_response.json()["id"]

    # Test with overlapping transformations where order matters
    # Test Case 1: uppercase then lowercase
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "formatter",
        "config": {
            "rules": ["uppercase", "lowercase"]
        }
    })

    run_response1 = client.post(f"/workflows/{workflow_id}/run")
    job_id1 = run_response1.json()["job_id"]

    # Create second workflow
    create_response2 = client.post("/workflows", json={"name": "Order Dependency Test 2"})
    workflow_id2 = create_response2.json()["id"]

    # Test Case 2: lowercase then uppercase
    client.post(f"/workflows/{workflow_id2}/nodes", json={
        "node_type": "formatter",
        "config": {
            "rules": ["lowercase", "uppercase"]
        }
    })

    run_response2 = client.post(f"/workflows/{workflow_id2}/run")
    job_id2 = run_response2.json()["job_id"]

    # Wait for completion
    import time
    time.sleep(2)

    # Get results
    job_response1 = client.get(f"/jobs/{job_id1}")
    result1 = job_response1.json().get("final_output", "")

    job_response2 = client.get(f"/jobs/{job_id2}")
    result2 = job_response2.json().get("final_output", "")

    # Both should result in the last transformation applied
    # Input: "Initial text from document"
    # Case 1: uppercase then lowercase -> "initial text from document"
    # Case 2: lowercase then uppercase -> "INITIAL TEXT FROM DOCUMENT"
    assert result1.strip() == "initial text from document"
    assert result2.strip() == "INITIAL TEXT FROM DOCUMENT"
    assert result1 != result2  # Order does matter here


def test_formatter_rules_invalid_order(client):
    """Integration test: invalid formatter rules should be rejected"""
    create_response = client.post("/workflows", json={"name": "Invalid Rules Test"})
    workflow_id = create_response.json()["id"]

    # Try to add a formatter node with invalid rules
    invalid_response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "formatter",
        "config": {
            "rules": ["invalid_rule", "another_invalid"]
        }
    })

    # Should reject invalid rules
    assert invalid_response.status_code == 400
    assert "detail" in invalid_response.json()


def test_formatter_rules_empty_list(client):
    """Integration test: empty rules list should pass through unchanged"""
    create_response = client.post("/workflows", json={"name": "Empty Rules Test"})
    workflow_id = create_response.json()["id"]

    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "formatter",
        "config": {
            "rules": []  # Empty rules
        }
    })

    run_response = client.post(f"/workflows/{workflow_id}/run")
    job_id = run_response.json()["job_id"]

    # Wait for completion
    import time
    time.sleep(2)

    job_response = client.get(f"/jobs/{job_id}")
    result = job_response.json().get("final_output", "")

    # Should be unchanged from the default input
    assert result.strip() == "Initial text from document"