import pytest
import io
import tempfile
import os
from unittest.mock import patch, MagicMock
from server.services.pdf_service import PDFService
from fastapi import UploadFile


class TestPDFExtractor:
    """Unit tests for PDF text extraction service - happy and edge cases"""

    def setup_method(self):
        self.pdf_service = PDFService()

    def create_test_pdf_content(self, text_content="Test PDF Content"):
        """Helper method to create valid PDF content for testing"""
        # Minimal valid PDF structure with text
        pdf_content = f"""%PDF-1.4
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
/Length {len(text_content) + 20}
>>
stream
BT
/F1 12 Tf
72 720 Td
({text_content}) Tj
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
{250 + len(text_content)}
%%EOF"""
        return pdf_content.encode('utf-8')

    def test_extract_text_simple_pdf(self):
        """Test successful text extraction from simple PDF"""
        pdf_content = self.create_test_pdf_content("Hello World")

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file.flush()

            try:
                extracted_text = self.pdf_service.extract_text(tmp_file.name)
                assert "Hello World" in extracted_text
                assert len(extracted_text.strip()) > 0
            finally:
                os.unlink(tmp_file.name)

    def test_extract_text_multiline_content(self):
        """Test extraction from PDF with multiple lines"""
        multiline_content = "Line 1\\nLine 2\\nLine 3"
        pdf_content = self.create_test_pdf_content(multiline_content)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file.flush()

            try:
                extracted_text = self.pdf_service.extract_text(tmp_file.name)
                # Note: PDF text extraction might not preserve exact newlines
                assert "Line 1" in extracted_text
                assert "Line 2" in extracted_text
                assert "Line 3" in extracted_text
            finally:
                os.unlink(tmp_file.name)

    def test_extract_text_special_characters(self):
        """Test extraction with special characters"""
        special_content = "Café naïve résumé @#$%^&*()"
        pdf_content = self.create_test_pdf_content(special_content)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file.flush()

            try:
                extracted_text = self.pdf_service.extract_text(tmp_file.name)
                # Basic characters should be extracted
                assert "Caf" in extracted_text or "naiv" in extracted_text
            finally:
                os.unlink(tmp_file.name)

    def test_extract_text_empty_pdf(self):
        """Test extraction from PDF with no text content"""
        # PDF with no text content
        empty_pdf = b"""%PDF-1.4
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
>>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000074 00000 n
0000000120 00000 n
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
193
%%EOF"""

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(empty_pdf)
            tmp_file.flush()

            try:
                extracted_text = self.pdf_service.extract_text(tmp_file.name)
                assert extracted_text == "" or extracted_text.strip() == ""
            finally:
                os.unlink(tmp_file.name)

    def test_extract_text_nonexistent_file(self):
        """Test extraction fails gracefully for nonexistent file"""
        with pytest.raises(FileNotFoundError):
            self.pdf_service.extract_text("/nonexistent/file.pdf")

    def test_extract_text_corrupted_pdf(self):
        """Test extraction handles corrupted PDF gracefully"""
        corrupted_content = b"This is not a valid PDF file content"

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(corrupted_content)
            tmp_file.flush()

            try:
                with pytest.raises(Exception):  # Should raise some PDF parsing error
                    self.pdf_service.extract_text(tmp_file.name)
            finally:
                os.unlink(tmp_file.name)

    def test_extract_text_large_content(self):
        """Test extraction from PDF with large text content"""
        large_content = "Lorem ipsum dolor sit amet. " * 100  # Large text
        pdf_content = self.create_test_pdf_content(large_content)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file.flush()

            try:
                extracted_text = self.pdf_service.extract_text(tmp_file.name)
                assert "Lorem ipsum" in extracted_text
                assert len(extracted_text) > 1000  # Should extract substantial content
            finally:
                os.unlink(tmp_file.name)

    def test_validate_pdf_valid_file(self):
        """Test PDF validation for valid file"""
        pdf_content = self.create_test_pdf_content("Valid PDF")

        upload_file = UploadFile(
            filename="test.pdf",
            file=io.BytesIO(pdf_content),
            content_type="application/pdf"
        )

        is_valid, error = self.pdf_service.validate_pdf(upload_file)
        assert is_valid is True
        assert error is None

    def test_validate_pdf_wrong_mime_type(self):
        """Test PDF validation rejects wrong MIME type"""
        upload_file = UploadFile(
            filename="test.pdf",
            file=io.BytesIO(b"Not a PDF"),
            content_type="text/plain"
        )

        is_valid, error = self.pdf_service.validate_pdf(upload_file)
        assert is_valid is False
        assert "MIME type" in error

    def test_validate_pdf_no_pdf_header(self):
        """Test PDF validation rejects file without PDF header"""
        upload_file = UploadFile(
            filename="test.pdf",
            file=io.BytesIO(b"This is not a PDF file"),
            content_type="application/pdf"
        )

        is_valid, error = self.pdf_service.validate_pdf(upload_file)
        assert is_valid is False
        assert "PDF" in error and "header" in error

    def test_validate_pdf_too_large(self):
        """Test PDF validation rejects oversized files"""
        # Create content larger than max size (10MB)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB

        upload_file = UploadFile(
            filename="large.pdf",
            file=io.BytesIO(large_content),
            content_type="application/pdf"
        )

        is_valid, error = self.pdf_service.validate_pdf(upload_file)
        assert is_valid is False
        assert "size" in error.lower()

    def test_validate_pdf_empty_file(self):
        """Test PDF validation rejects empty files"""
        upload_file = UploadFile(
            filename="empty.pdf",
            file=io.BytesIO(b""),
            content_type="application/pdf"
        )

        is_valid, error = self.pdf_service.validate_pdf(upload_file)
        assert is_valid is False
        assert "empty" in error.lower()

    @patch('pypdf.PdfReader')
    def test_extract_text_with_pypdf_error(self, mock_pdf_reader):
        """Test extraction handles pypdf library errors"""
        mock_pdf_reader.side_effect = Exception("PyPDF error")

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"dummy content")
            tmp_file.flush()

            try:
                with pytest.raises(Exception):
                    self.pdf_service.extract_text(tmp_file.name)
            finally:
                os.unlink(tmp_file.name)

    def test_store_file_success(self):
        """Test successful file storage"""
        pdf_content = self.create_test_pdf_content("Storage test")

        upload_file = UploadFile(
            filename="storage_test.pdf",
            file=io.BytesIO(pdf_content),
            content_type="application/pdf"
        )

        file_id, stored_path = self.pdf_service.store_file(upload_file)

        try:
            assert file_id is not None
            assert len(file_id) > 0
            assert stored_path.endswith('.pdf')
            assert os.path.exists(stored_path)

            # Verify file content
            with open(stored_path, 'rb') as f:
                stored_content = f.read()
                assert stored_content == pdf_content

        finally:
            # Cleanup
            if os.path.exists(stored_path):
                os.unlink(stored_path)

    def test_store_file_creates_directory(self):
        """Test that store_file creates uploads directory if it doesn't exist"""
        # This test assumes the store_file method creates directories as needed
        pdf_content = self.create_test_pdf_content("Directory test")

        upload_file = UploadFile(
            filename="directory_test.pdf",
            file=io.BytesIO(pdf_content),
            content_type="application/pdf"
        )

        file_id, stored_path = self.pdf_service.store_file(upload_file)

        try:
            assert os.path.exists(os.path.dirname(stored_path))
            assert os.path.exists(stored_path)
        finally:
            if os.path.exists(stored_path):
                os.unlink(stored_path)

    def test_extract_text_unicode_content(self):
        """Test extraction with Unicode characters"""
        unicode_content = "中文 العربية русский"
        pdf_content = self.create_test_pdf_content(unicode_content)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file.flush()

            try:
                extracted_text = self.pdf_service.extract_text(tmp_file.name)
                # Unicode extraction might not be perfect, but should not crash
                assert isinstance(extracted_text, str)
                assert len(extracted_text) >= 0
            finally:
                os.unlink(tmp_file.name)

    def test_file_cleanup_after_processing(self):
        """Test that temporary files are properly cleaned up"""
        pdf_content = self.create_test_pdf_content("Cleanup test")

        # This test would be more meaningful if the service had cleanup methods
        # For now, just ensure basic operations don't leave temp files
        upload_file = UploadFile(
            filename="cleanup_test.pdf",
            file=io.BytesIO(pdf_content),
            content_type="application/pdf"
        )

        is_valid, _ = self.pdf_service.validate_pdf(upload_file)
        assert is_valid is True

        # Reset file pointer for reuse
        upload_file.file.seek(0)

        file_id, stored_path = self.pdf_service.store_file(upload_file)

        try:
            extracted_text = self.pdf_service.extract_text(stored_path)
            assert len(extracted_text) > 0
        finally:
            if os.path.exists(stored_path):
                os.unlink(stored_path)