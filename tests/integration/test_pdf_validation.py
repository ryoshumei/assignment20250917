import pytest
from fastapi.testclient import TestClient
from server.main import app
import io


@pytest.fixture
def client():
    return TestClient(app)


def test_pdf_validation_valid_pdf(client):
    """Integration test: valid PDF should be accepted"""
    # Create a valid minimal PDF
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF Content) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \n0000000179 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n253\n%%EOF"

    files = {"file": ("valid.pdf", io.BytesIO(pdf_content), "application/pdf")}
    response = client.post("/files", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
    assert data["filename"] == "valid.pdf"


def test_pdf_validation_mime_type_check(client):
    """Integration test: non-PDF MIME type should be rejected"""
    # Text file with PDF extension (should be caught by MIME validation)
    fake_pdf_content = b"This is not a PDF file"

    files = {"file": ("fake.pdf", io.BytesIO(fake_pdf_content), "text/plain")}
    response = client.post("/files", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "mime" in data["detail"].lower() or "pdf" in data["detail"].lower()


def test_pdf_validation_file_size_limit(client):
    """Integration test: oversized PDF should be rejected"""
    # Create a PDF that exceeds size limit (assume 10MB limit)
    large_pdf_header = b"%PDF-1.4\n"
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB
    large_pdf_footer = b"\n%%EOF"
    large_pdf = large_pdf_header + large_content + large_pdf_footer

    files = {"file": ("large.pdf", io.BytesIO(large_pdf), "application/pdf")}
    response = client.post("/files", files=files)

    assert response.status_code == 413  # Payload too large
    data = response.json()
    assert "detail" in data
    assert "size" in data["detail"].lower() or "large" in data["detail"].lower()


def test_pdf_validation_corrupted_pdf(client):
    """Integration test: corrupted PDF should be rejected"""
    # Corrupted PDF content (missing required PDF structure)
    corrupted_pdf = b"%PDF-1.4\ngarbage content without proper PDF structure"

    files = {"file": ("corrupted.pdf", io.BytesIO(corrupted_pdf), "application/pdf")}
    response = client.post("/files", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert ("corrupted" in data["detail"].lower() or
            "invalid" in data["detail"].lower() or
            "pdf" in data["detail"].lower())


def test_pdf_validation_encrypted_pdf(client):
    """Integration test: encrypted PDF should be rejected with clear message"""
    # Minimal encrypted PDF structure (simplified for testing)
    encrypted_pdf = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
/Encrypt 3 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [4 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Filter /Standard
/V 1
/R 2
/O <encrypted_owner_password>
/U <encrypted_user_password>
/P -44
>>
endobj
4 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000074 00000 n
0000000120 00000 n
0000000250 00000 n
trailer
<<
/Size 5
/Root 1 0 R
/Encrypt 3 0 R
>>
startxref
320
%%EOF"""

    files = {"file": ("encrypted.pdf", io.BytesIO(encrypted_pdf), "application/pdf")}
    response = client.post("/files", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert ("encrypted" in data["detail"].lower() or
            "password" in data["detail"].lower() or
            "protected" in data["detail"].lower())


def test_pdf_validation_empty_file(client):
    """Integration test: empty file should be rejected"""
    empty_content = b""

    files = {"file": ("empty.pdf", io.BytesIO(empty_content), "application/pdf")}
    response = client.post("/files", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "empty" in data["detail"].lower() or "size" in data["detail"].lower()


def test_pdf_validation_no_file_extension(client):
    """Integration test: file without .pdf extension should be handled gracefully"""
    # Valid PDF content but no .pdf extension
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n193\n%%EOF"

    files = {"file": ("document", io.BytesIO(pdf_content), "application/pdf")}
    response = client.post("/files", files=files)

    # Should accept based on MIME type, not extension
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data


def test_pdf_text_extraction_success(client):
    """Integration test: PDF text extraction should work for valid PDFs"""
    # Create workflow with extract_text node
    create_response = client.post("/workflows", json={"name": "PDF Extraction Test"})
    workflow_id = create_response.json()["id"]

    # Upload a PDF with text content
    pdf_with_text = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello PDF World!) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000074 00000 n
0000000120 00000 n
0000000179 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
253
%%EOF"""

    files = {"file": ("text_pdf.pdf", io.BytesIO(pdf_with_text), "application/pdf")}
    upload_response = client.post("/files", files=files)
    file_id = upload_response.json()["file_id"]

    # Add extract_text node
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "extract_text",
        "config": {"file_id": file_id}
    })

    # Run workflow
    run_response = client.post(f"/workflows/{workflow_id}/run")
    job_id = run_response.json()["job_id"]

    # Wait for completion
    import time
    time.sleep(3)

    # Check extracted text
    job_response = client.get(f"/jobs/{job_id}")
    job_data = job_response.json()

    assert job_data["status"] == "Succeeded"
    assert "final_output" in job_data
    # Should contain the text from the PDF
    assert "Hello PDF World!" in job_data["final_output"]


def test_pdf_text_extraction_failure_handling(client):
    """Integration test: PDF text extraction should handle failures gracefully"""
    # Create workflow
    create_response = client.post("/workflows", json={"name": "PDF Extraction Failure Test"})
    workflow_id = create_response.json()["id"]

    # Add extract_text node with invalid file_id
    client.post(f"/workflows/{workflow_id}/nodes", json={
        "node_type": "extract_text",
        "config": {"file_id": "nonexistent-file-id"}
    })

    # Run workflow
    run_response = client.post(f"/workflows/{workflow_id}/run")
    job_id = run_response.json()["job_id"]

    # Wait for completion
    import time
    time.sleep(3)

    # Check that failure is handled gracefully
    job_response = client.get(f"/jobs/{job_id}")
    job_data = job_response.json()

    assert job_data["status"] == "Failed"
    assert "error_message" in job_data
    assert job_data["error_message"] is not None
    # Error should be descriptive
    error_msg = job_data["error_message"].lower()
    assert "file" in error_msg and ("not found" in error_msg or "exist" in error_msg)