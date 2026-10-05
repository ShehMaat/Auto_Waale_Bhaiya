import hashlib
import io
import logging
import re

import docx
import pymupdf

logger = logging.getLogger(__name__)


class UnsupportedFileError(Exception):
    pass


class DocumentParser:
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    SUPPORTED_MIMES = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    }

    @staticmethod
    def validate_file(file_bytes: bytes, mime_type: str, filename: str) -> bool:
        if len(file_bytes) > DocumentParser.MAX_FILE_SIZE:
            raise ValueError("File exceeds maximum allowed size of 10MB.")
        if mime_type not in DocumentParser.SUPPORTED_MIMES:
            raise ValueError(f"Unsupported MIME type: {mime_type}. Only PDF and DOCX are allowed.")
        return True

    @staticmethod
    def extract_text_from_bytes(file_bytes: bytes, mime_type: str) -> str:
        """Extracts text from PDF or DOCX file bytes."""
        text = ""
        if mime_type == "application/pdf":
            text = DocumentParser._extract_from_pdf(file_bytes)
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = DocumentParser._extract_from_docx(file_bytes)
        else:
            raise ValueError("Unsupported file format. Please upload a PDF or DOCX.")

        return DocumentParser._normalize_text(text)

    @staticmethod
    def _extract_from_pdf(file_bytes: bytes) -> str:
        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")  # type: ignore[no-untyped-call]
            text = ""
            for page in doc:  # type: ignore[attr-defined]
                text += page.get_text() + "\n"

            # Very basic OCR fallback logic placeholder
            if len(text.strip()) < 50 and len(doc) > 0:
                logger.warning("PDF appears to be scanned/image-based. Applying OCR fallback.")
                text = DocumentParser._ocr_fallback(file_bytes)

            return text
        except Exception as e:
            logger.error(f"Failed to parse PDF: {str(e)}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")  # noqa: B904

    @staticmethod
    def _extract_from_docx(file_bytes: bytes) -> str:
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"Failed to parse DOCX: {str(e)}")
            raise ValueError(f"Failed to parse DOCX: {str(e)}")  # noqa: B904

    @staticmethod
    def _ocr_fallback(file_bytes: bytes) -> str:
        """OCR is a deferred Phase 2 feature. Do not return hallucinated content."""
        raise UnsupportedFileError(
            "OCR is currently unsupported. File appears to be scanned/image-based."
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        # Simple whitespace normalization
        text = re.sub(r"\s+", " ", text)
        # Remove non-printable characters
        text = re.sub(r"[^\x20-\x7E]", "", text)
        return text.strip()

    @staticmethod
    def compute_hash(file_bytes: bytes) -> str:
        """Computes SHA-256 hash of the file for deduplication."""
        return hashlib.sha256(file_bytes).hexdigest()
