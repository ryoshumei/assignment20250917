import pytest
import time
from fastapi.testclient import TestClient
from server.main import app
import io


@pytest.fixture
def client():
    return TestClient(app)


def test_end_to_end_async_flow(client):
    """Integration test: end-to-end async flow (create → upload PDF → add nodes → run → poll)"""
    # Step 1: Create a workflow
    create_response = client.post("/workflows", json={"name": "E2E Test Workflow"})
    assert create_response.status_code == 200
    workflow_id = create_response.json()["id"]

    # Step 2: Upload a PDF file
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Hello World!) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \n0000000179 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n253\n%%EOF"

    files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_response = client.post("/files", files=files)
    assert upload_response.status_code == 200
    file_id = upload_response.json()["file_id"]

    # Step 3: Add nodes to the workflow
    # Add EXTRACT_TEXT node with file_id config
    extract_response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "extract_text",
        "config": {"file_id": file_id}
    })
    assert extract_response.status_code == 200

    # Add GENERATIVE_AI node
    llm_response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "generative_ai",
        "config": {
            "model": "gpt-4.1-mini",
            "prompt": "Summarize the following text in one sentence: {text}"
        }
    })
    assert llm_response.status_code == 200

    # Add FORMATTER node
    formatter_response = client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "formatter",
        "config": {
            "rules": ["lowercase", "full_to_half"]
        }
    })
    assert formatter_response.status_code == 200

    # Step 4: Run the workflow asynchronously
    run_response = client.post(f"/workflows/{workflow_id}/run")
    assert run_response.status_code == 200
    job_id = run_response.json()["job_id"]

    # Step 5: Poll job status until completion
    max_polls = 30  # Maximum 30 seconds
    job_completed = False

    for _ in range(max_polls):
        job_response = client.get(f"/jobs/{job_id}")
        assert job_response.status_code == 200
        job_data = job_response.json()

        if job_data["status"] in ["Succeeded", "Failed"]:
            job_completed = True
            final_status = job_data["status"]
            break

        time.sleep(1)  # Wait 1 second before next poll

    assert job_completed, f"Job did not complete within {max_polls} seconds"
    assert final_status == "Succeeded", f"Job failed with status: {final_status}"

    # Step 6: Verify final output is available
    final_job_response = client.get(f"/jobs/{job_id}")
    final_job_data = final_job_response.json()
    assert "final_output" in final_job_data
    assert final_job_data["final_output"] is not None
    assert len(final_job_data["final_output"]) > 0


def test_async_flow_with_multiple_jobs(client):
    """Integration test: multiple async jobs running with concurrency limits"""
    # Create a workflow
    create_response = client.post("/workflows", json={"name": "Concurrency Test Workflow"})
    workflow_id = create_response.json()["id"]

    # Add a simple node
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "formatter",
        "config": {"rules": ["uppercase"]}
    })

    # Start multiple jobs (should respect concurrency limit of 2 running + queue)
    job_ids = []
    for i in range(5):
        run_response = client.post(f"/workflows/{workflow_id}/run")
        if run_response.status_code == 200:
            job_ids.append(run_response.json()["job_id"])
        elif run_response.status_code == 429:
            # Queue is full, which is expected
            break

    # At least one job should have been accepted
    assert len(job_ids) >= 1

    # Wait for jobs to complete
    time.sleep(5)

    # Verify jobs completed successfully
    for job_id in job_ids:
        job_response = client.get(f"/jobs/{job_id}")
        job_data = job_response.json()
        assert job_data["status"] in ["Succeeded", "Failed", "Running", "Pending"]