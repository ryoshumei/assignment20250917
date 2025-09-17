import pytest
import time
import asyncio
from fastapi.testclient import TestClient
from server.main import app
import io


@pytest.fixture
def client():
    return TestClient(app)


class TestPerformanceValidation:
    """Performance validation tests - ensure system meets response time expectations"""

    def test_workflow_creation_performance(self, client):
        """Test workflow creation completes within acceptable time"""
        start_time = time.time()

        response = client.post("/workflows", json={"name": "Performance Test Workflow"})

        execution_time = time.time() - start_time

        assert response.status_code == 200
        assert execution_time < 2.0, f"Workflow creation took {execution_time:.2f}s, expected < 2.0s"

    def test_file_upload_performance(self, client):
        """Test PDF file upload completes within acceptable time"""
        # Create a reasonably sized PDF (around 100KB)
        pdf_content = b"%PDF-1.4\n" + b"Test content " * 5000 + b"\n%%EOF"

        start_time = time.time()

        files = {"file": ("performance_test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        response = client.post("/files", files=files)

        execution_time = time.time() - start_time

        assert response.status_code == 200
        assert execution_time < 5.0, f"File upload took {execution_time:.2f}s, expected < 5.0s"

    def test_node_addition_performance(self, client):
        """Test adding nodes to workflow completes quickly"""
        # Create workflow first
        workflow_response = client.post("/workflows", json={"name": "Node Performance Test"})
        workflow_id = workflow_response.json()["id"]

        start_time = time.time()

        # Add a generative AI node
        response = client.post(f"/workflows/{workflow_id}/nodes", json={
            "node_type": "generative_ai",
            "config": {
                "model": "gpt-4.1-mini",
                "prompt": "Summarize: {text}"
            }
        })

        execution_time = time.time() - start_time

        assert response.status_code == 200
        assert execution_time < 1.0, f"Node addition took {execution_time:.2f}s, expected < 1.0s"

    def test_job_status_polling_performance(self, client):
        """Test job status polling returns within acceptable time"""
        # Create workflow and add a simple formatter node
        workflow_response = client.post("/workflows", json={"name": "Polling Test"})
        workflow_id = workflow_response.json()["id"]

        client.post(f"/workflows/{workflow_id}/nodes", json={
            "node_type": "formatter",
            "config": {"rules": ["lowercase"]}
        })

        # Start job
        run_response = client.post(f"/workflows/{workflow_id}/run")
        job_id = run_response.json()["job_id"]

        # Test polling performance
        start_time = time.time()

        response = client.get(f"/jobs/{job_id}")

        execution_time = time.time() - start_time

        assert response.status_code == 200
        assert execution_time < 1.0, f"Job status polling took {execution_time:.2f}s, expected < 1.0s"

    def test_workflow_execution_performance(self, client):
        """Test complete workflow execution completes within reasonable time"""
        # Create workflow
        workflow_response = client.post("/workflows", json={"name": "Execution Performance Test"})
        workflow_id = workflow_response.json()["id"]

        # Add a simple formatter node (no external API calls)
        client.post(f"/workflows/{workflow_id}/nodes", json={
            "node_type": "formatter",
            "config": {"rules": ["lowercase", "full_to_half"]}
        })

        start_time = time.time()

        # Run workflow
        run_response = client.post(f"/workflows/{workflow_id}/run")
        job_id = run_response.json()["job_id"]

        # Poll until completion
        max_polls = 30
        for _ in range(max_polls):
            job_response = client.get(f"/jobs/{job_id}")
            job_data = job_response.json()

            if job_data["status"] in ["Succeeded", "Failed"]:
                break

            time.sleep(0.5)

        execution_time = time.time() - start_time

        assert job_data["status"] == "Succeeded"
        assert execution_time < 15.0, f"Workflow execution took {execution_time:.2f}s, expected < 15.0s"

    def test_concurrent_requests_performance(self, client):
        """Test system handles multiple concurrent requests efficiently"""
        import threading
        import queue

        results = queue.Queue()

        def create_workflow(thread_id):
            start_time = time.time()
            try:
                response = client.post("/workflows", json={"name": f"Concurrent Test {thread_id}"})
                execution_time = time.time() - start_time
                results.put((thread_id, response.status_code, execution_time))
            except Exception as e:
                results.put((thread_id, 500, time.time() - start_time))

        # Start 5 concurrent workflow creation requests
        threads = []
        overall_start = time.time()

        for i in range(5):
            thread = threading.Thread(target=create_workflow, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        overall_time = time.time() - overall_start

        # Collect results
        execution_times = []
        success_count = 0

        while not results.empty():
            thread_id, status_code, exec_time = results.get()
            execution_times.append(exec_time)
            if status_code == 200:
                success_count += 1

        # Validate performance
        assert success_count >= 4, f"Only {success_count}/5 concurrent requests succeeded"
        assert overall_time < 10.0, f"Concurrent requests took {overall_time:.2f}s, expected < 10.0s"
        assert max(execution_times) < 5.0, f"Slowest request took {max(execution_times):.2f}s, expected < 5.0s"

    def test_large_workflow_performance(self, client):
        """Test workflow with multiple nodes performs adequately"""
        # Create workflow
        workflow_response = client.post("/workflows", json={"name": "Large Workflow Test"})
        workflow_id = workflow_response.json()["id"]

        start_time = time.time()

        # Add multiple nodes
        for i in range(5):
            client.post(f"/workflows/{workflow_id}/nodes", json={
                "node_type": "formatter",
                "config": {"rules": ["lowercase"] if i % 2 == 0 else ["uppercase"]}
            })

        node_addition_time = time.time() - start_time

        # Run workflow
        run_start = time.time()
        run_response = client.post(f"/workflows/{workflow_id}/run")
        job_id = run_response.json()["job_id"]

        # Poll for completion
        max_polls = 60
        for _ in range(max_polls):
            job_response = client.get(f"/jobs/{job_id}")
            job_data = job_response.json()

            if job_data["status"] in ["Succeeded", "Failed"]:
                break

            time.sleep(0.5)

        total_execution_time = time.time() - run_start

        assert job_data["status"] == "Succeeded"
        assert node_addition_time < 5.0, f"Adding 5 nodes took {node_addition_time:.2f}s, expected < 5.0s"
        assert total_execution_time < 30.0, f"5-node workflow execution took {total_execution_time:.2f}s, expected < 30.0s"

    def test_memory_usage_stability(self, client):
        """Test that repeated operations don't cause memory leaks"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform repeated operations
        for i in range(10):
            # Create workflow
            workflow_response = client.post("/workflows", json={"name": f"Memory Test {i}"})
            workflow_id = workflow_response.json()["id"]

            # Add node
            client.post(f"/workflows/{workflow_id}/nodes", json={
                "node_type": "formatter",
                "config": {"rules": ["lowercase"]}
            })

            # Run workflow
            run_response = client.post(f"/workflows/{workflow_id}/run")
            job_id = run_response.json()["job_id"]

            # Wait for completion
            for _ in range(20):
                job_response = client.get(f"/jobs/{job_id}")
                if job_response.json()["status"] in ["Succeeded", "Failed"]:
                    break
                time.sleep(0.1)

        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB

        # Allow for some memory growth but not excessive
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB, expected < 100MB"

    def test_api_response_times_documentation(self, client):
        """Document expected API response times for reference"""
        endpoints_performance = {}

        # Test workflow creation
        start = time.time()
        client.post("/workflows", json={"name": "Response Time Test"})
        endpoints_performance["POST /workflows"] = time.time() - start

        # Test workflow retrieval
        workflow_response = client.post("/workflows", json={"name": "Retrieval Test"})
        workflow_id = workflow_response.json()["id"]

        start = time.time()
        client.get(f"/workflows/{workflow_id}")
        endpoints_performance["GET /workflows/{id}"] = time.time() - start

        # Test node addition
        start = time.time()
        client.post(f"/workflows/{workflow_id}/nodes", json={
            "node_type": "formatter",
            "config": {"rules": ["lowercase"]}
        })
        endpoints_performance["POST /workflows/{id}/nodes"] = time.time() - start

        # Test job initiation
        start = time.time()
        run_response = client.post(f"/workflows/{workflow_id}/run")
        endpoints_performance["POST /workflows/{id}/run"] = time.time() - start

        job_id = run_response.json()["job_id"]

        # Test job status
        start = time.time()
        client.get(f"/jobs/{job_id}")
        endpoints_performance["GET /jobs/{id}"] = time.time() - start

        # Print performance summary for documentation
        print("\n=== API Performance Summary ===")
        for endpoint, duration in endpoints_performance.items():
            print(f"{endpoint}: {duration:.3f}s")

        # All endpoints should respond quickly
        for endpoint, duration in endpoints_performance.items():
            assert duration < 2.0, f"{endpoint} took {duration:.3f}s, expected < 2.0s"

    def test_database_query_performance(self, client):
        """Test database operations perform within acceptable limits"""
        # Create multiple workflows to test query performance
        workflow_ids = []

        creation_start = time.time()
        for i in range(10):
            response = client.post("/workflows", json={"name": f"DB Test Workflow {i}"})
            workflow_ids.append(response.json()["id"])
        creation_time = time.time() - creation_start

        # Test retrieval performance
        retrieval_start = time.time()
        for workflow_id in workflow_ids:
            client.get(f"/workflows/{workflow_id}")
        retrieval_time = time.time() - retrieval_start

        assert creation_time < 10.0, f"Creating 10 workflows took {creation_time:.2f}s, expected < 10.0s"
        assert retrieval_time < 5.0, f"Retrieving 10 workflows took {retrieval_time:.2f}s, expected < 5.0s"

    def test_error_handling_performance(self, client):
        """Test that error cases don't cause performance degradation"""
        error_tests = [
            ("GET", "/workflows/nonexistent-id", None),
            ("POST", "/workflows/invalid-id/nodes", {"invalid": "data"}),
            ("GET", "/jobs/nonexistent-job-id", None),
        ]

        for method, endpoint, data in error_tests:
            start_time = time.time()

            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json=data)

            execution_time = time.time() - start_time

            # Error responses should still be fast
            assert execution_time < 1.0, f"Error case {method} {endpoint} took {execution_time:.2f}s, expected < 1.0s"
            assert response.status_code >= 400  # Should be an error response