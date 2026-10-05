import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from packages.browser.errors import BrowserUploadError
from packages.browser.policies import BrowserSecurityPolicy
from packages.db.models.candidate import Document


class BrowserUploadManager:
    """Manages secure file uploads mapping logical document IDs to actual files."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def resolve_upload_document(
        self, user_id: uuid.UUID, document_id: str, local_temp_dir: str
    ) -> str:
        """
        Resolves a logical document ID to a safe local file path.
        In a real scenario, this fetches the file from MinIO to a temporary local path
        so Playwright can upload it, without exposing arbitrary filesystem access.
        """
        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError as e:
            raise BrowserUploadError("Invalid document ID format") from e

        doc = (
            self.db_session.query(Document)
            .filter(Document.id == doc_uuid, Document.user_id == user_id)
            .first()
        )

        if not doc:
            raise BrowserUploadError("Document not found or unauthorized")

        # Validate against policy
        BrowserSecurityPolicy.validate_upload(doc.file_size)

        # Assuming the document was fetched securely to local_temp_dir
        # We simulate the local path here for the scope of Phase 3A
        safe_dir = Path(local_temp_dir).resolve()
        target_path = (safe_dir / f"{doc.id}_{doc.filename}").resolve()

        # Prevent traversal
        if not target_path.is_relative_to(safe_dir):
            raise BrowserUploadError("Path traversal detected in upload resolution")

        # In full implementation, we'd pull from S3 to target_path here if it doesn't exist

        return str(target_path)
