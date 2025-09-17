import os
import uuid
from typing import Optional, Tuple
import pypdf
from fastapi import UploadFile, HTTPException
import logging

logger = logging.getLogger(__name__)

class PDFService:
    """Service for handling PDF file operations"""

    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        self.max_file_size = 10 * 1024 * 1024  # 10MB limit
        self.allowed_mime_types = ["application/pdf"]

        # Create upload directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)

    def validate_pdf(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded PDF file
        Returns: (is_valid, error_message)
        """
        try:
            # Check MIME type
            if file.content_type not in self.allowed_mime_types:
                return False, f"Invalid file type. Expected PDF, got {file.content_type}"

            # Read file content for validation
            file_content = file.file.read()
            file.file.seek(0)  # Reset file pointer

            # Check file size
            if len(file_content) == 0:
                return False, "Empty file uploaded"

            if len(file_content) > self.max_file_size:
                return False, f"FILE_TOO_LARGE:File too large. Maximum size: {self.max_file_size / (1024*1024):.1f}MB"

            # Check if it's actually a PDF by reading the header
            if not file_content.startswith(b'%PDF-'):
                return False, "File is not a valid PDF document"

            # Try to parse PDF to ensure it's not corrupted
            try:
                import io
                pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))

                # Check if PDF is encrypted
                if pdf_reader.is_encrypted:
                    return False, "Encrypted PDFs are not supported"

                # Try to access first page to ensure PDF is readable
                if len(pdf_reader.pages) == 0:
                    return False, "PDF has no pages"

                # Test that we can read the first page
                _ = pdf_reader.pages[0]

            except Exception as e:
                logger.warning(f"PDF validation failed: {str(e)}")
                return False, "PDF file is corrupted or invalid"

            return True, None

        except Exception as e:
            logger.error(f"Error validating PDF: {str(e)}")
            return False, f"Error validating file: {str(e)}"

    def store_file(self, file: UploadFile) -> Tuple[str, str]:
        """
        Store uploaded file to disk
        Returns: (file_id, file_path)
        """
        try:
            # Generate unique file ID and path
            file_id = str(uuid.uuid4())
            file_extension = os.path.splitext(file.filename or "file.pdf")[1] or ".pdf"
            filename = f"{file_id}{file_extension}"
            file_path = os.path.join(self.upload_dir, filename)

            # Read and write file content
            file_content = file.file.read()
            file.file.seek(0)  # Reset file pointer

            with open(file_path, "wb") as f:
                f.write(file_content)

            logger.info(f"File stored successfully: {file_path}")
            return file_id, file_path

        except Exception as e:
            logger.error(f"Error storing file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error storing file: {str(e)}")

    def extract_text(self, file_path: str) -> str:
        """
        Extract text content from PDF file
        Returns: extracted text content
        """
        try:
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")

            with open(file_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)

                if pdf_reader.is_encrypted:
                    raise HTTPException(status_code=400, detail="Cannot extract text from encrypted PDF")

                text_content = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text_content += page.extract_text() + "\n"
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                        continue

                if not text_content.strip():
                    logger.warning(f"No text extracted from PDF: {file_path}")
                    return "No text content found in PDF"

                logger.info(f"Successfully extracted text from PDF: {len(text_content)} characters")
                return text_content.strip()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error extracting text from PDF: {str(e)}")

    def get_file_info(self, file_path: str) -> dict:
        """
        Get information about a stored file
        Returns: file information dict
        """
        try:
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")

            stat = os.stat(file_path)
            return {
                "size_bytes": stat.st_size,
                "created_at": stat.st_ctime,
                "exists": True
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error accessing file: {str(e)}")

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a stored file
        Returns: True if successful
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted: {file_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {str(e)}")
            return False


# Global service instance
pdf_service = PDFService()