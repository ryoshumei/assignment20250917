import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_llm_config_validation_valid(client):
    """Integration test: valid LLM config should be accepted"""
    create_response = client.post("/workflows", json={"name": "LLM Valid Config Test"})
    workflow_id = create_response.json()["id"]

    # Valid LLM configuration
    valid_config = {
        "model": "gpt-3.5-turbo",
        "prompt": "Summarize the following text: {text}",
        "max_tokens": 150,
        "temperature": 0.7
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "generative_ai",
        "config": valid_config
    })

    assert response.status_code == 200
    assert "node_id" in response.json()


def test_llm_config_validation_missing_model(client):
    """Integration test: LLM config missing model should be rejected"""
    create_response = client.post("/workflows", json={"name": "LLM Invalid Config Test"})
    workflow_id = create_response.json()["id"]

    # Missing required 'model' field
    invalid_config = {
        "prompt": "Summarize the following text: {text}",
        "max_tokens": 150
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "generative_ai",
        "config": invalid_config
    })

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "model" in data["detail"].lower()


def test_llm_config_validation_missing_prompt(client):
    """Integration test: LLM config missing prompt should be rejected"""
    create_response = client.post("/workflows", json={"name": "LLM Invalid Config Test"})
    workflow_id = create_response.json()["id"]

    # Missing required 'prompt' field
    invalid_config = {
        "model": "gpt-3.5-turbo",
        "max_tokens": 150
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "generative_ai",
        "config": invalid_config
    })

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "prompt" in data["detail"].lower()


def test_llm_config_validation_invalid_model(client):
    """Integration test: invalid model name should be rejected"""
    create_response = client.post("/workflows", json={"name": "LLM Invalid Model Test"})
    workflow_id = create_response.json()["id"]

    # Invalid model name
    invalid_config = {
        "model": "invalid-model-name",
        "prompt": "Summarize: {text}"
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "generative_ai",
        "config": invalid_config
    })

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "model" in data["detail"].lower()


def test_llm_config_validation_invalid_temperature(client):
    """Integration test: invalid temperature should be rejected"""
    create_response = client.post("/workflows", json={"name": "LLM Invalid Temp Test"})
    workflow_id = create_response.json()["id"]

    # Temperature out of valid range (should be 0.0-2.0)
    invalid_config = {
        "model": "gpt-3.5-turbo",
        "prompt": "Summarize: {text}",
        "temperature": 3.5  # Invalid: too high
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "generative_ai",
        "config": invalid_config
    })

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "temperature" in data["detail"].lower()


def test_llm_config_validation_invalid_max_tokens(client):
    """Integration test: invalid max_tokens should be rejected"""
    create_response = client.post("/workflows", json={"name": "LLM Invalid Tokens Test"})
    workflow_id = create_response.json()["id"]

    # max_tokens too high or negative
    invalid_config = {
        "model": "gpt-3.5-turbo",
        "prompt": "Summarize: {text}",
        "max_tokens": -50  # Invalid: negative
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "generative_ai",
        "config": invalid_config
    })

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_llm_config_prompt_placeholder_validation(client):
    """Integration test: prompt should contain {text} placeholder"""
    create_response = client.post("/workflows", json={"name": "LLM Prompt Validation Test"})
    workflow_id = create_response.json()["id"]

    # Prompt without {text} placeholder
    invalid_config = {
        "model": "gpt-3.5-turbo",
        "prompt": "This prompt has no placeholder for input text"
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "generative_ai",
        "config": invalid_config
    })

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "{text}" in data["detail"] or "placeholder" in data["detail"].lower()


def test_llm_execution_failure_messaging(client):
    """Integration test: LLM execution failures should provide clear error messages"""
    create_response = client.post("/workflows", json={"name": "LLM Failure Test"})
    workflow_id = create_response.json()["id"]

    # Add a valid LLM node (but will fail due to no API key or invalid endpoint)
    valid_config = {
        "model": "gpt-3.5-turbo",
        "prompt": "Summarize: {text}"
    }

    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "generative_ai",
        "config": valid_config
    })

    # Run the workflow (should fail during LLM call)
    run_response = client.post(f"/workflows/{workflow_id}/run")
    job_id = run_response.json()["job_id"]

    # Wait for completion
    import time
    time.sleep(3)

    # Check that error message is clear and helpful
    job_response = client.get(f"/jobs/{job_id}")
    job_data = job_response.json()

    if job_data["status"] == "Failed":
        assert "error_message" in job_data
        assert job_data["error_message"] is not None
        error_msg = job_data["error_message"].lower()

        # Should contain helpful context about the failure
        helpful_keywords = ["api", "key", "auth", "request", "llm", "connection", "timeout"]
        assert any(keyword in error_msg for keyword in helpful_keywords)


def test_llm_supported_models_list(client):
    """Integration test: only supported models should be accepted"""
    create_response = client.post("/workflows", json={"name": "Supported Models Test"})
    workflow_id = create_response.json()["id"]

    # Test supported models
    supported_models = [
        "gpt-4.1-mini",
        "gpt-4o",
        "gpt-5"
    ]

    for model in supported_models:
        config = {
            "model": model,
            "prompt": "Test prompt: {text}"
        }

        response = client.post(f"/workflows/{workflow_id}/nodes", json={
            "node_type": "generative_ai",
            "config": config
        })

        # Should accept all supported models
        assert response.status_code == 200

    # Test unsupported model
    unsupported_config = {
        "model": "unsupported-model-xyz",
        "prompt": "Test prompt: {text}"
    }

    response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "generative_ai",
        "config": unsupported_config
    })

    assert response.status_code == 400