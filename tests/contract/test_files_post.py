import pytest
from fastapi.testclient import TestClient
from server.main import app
import io


@pytest.fixture
def client():
    return TestClient(app)


def test_upload_pdf_file_contract(client):
    """Contract test for POST /files - PDF upload"""
    # Create a mock PDF file
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n193\n%%EOF"

    # Test uploading the PDF file
    files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    response = client.post("/files", files=files)

    assert response.status_code == 200
    data = response.json()

    # Verify response schema matches OpenAPI spec
    required_fields = ["file_id", "filename", "size"]
    for field in required_fields:
        assert field in data
        assert data[field] is not None

    assert isinstance(data["file_id"], str)
    assert data["filename"] == "test.pdf"
    assert isinstance(data["size"], int)
    assert data["size"] > 0


def test_upload_invalid_file_type_contract(client):
    """Contract test for POST /files - invalid file type"""
    # Create a non-PDF file
    txt_content = b"This is not a PDF file"

    files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
    response = client.post("/files", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_upload_oversized_file_contract(client):
    """Contract test for POST /files - file too large"""
    # Create a file that's too large (simulate 11MB)
    large_content = b"x" * (11 * 1024 * 1024)

    files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}
    response = client.post("/files", files=files)

    assert response.status_code == 413  # Payload too large
    data = response.json()
    assert "detail" in data


def test_upload_no_file_contract(client):
    """Contract test for POST /files - no file provided"""
    response = client.post("/files")

    assert response.status_code == 422  # Unprocessable entity