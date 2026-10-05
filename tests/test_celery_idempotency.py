from unittest.mock import patch

from apps.api.app.core.celery_tasks import process_document_task
from packages.db.models.candidate import Document


def test_process_document_idempotency(db_session) -> None:  # type: ignore[no-untyped-def]
    import uuid

    doc_id = uuid.uuid4()
    user_id = uuid.uuid4()
    # Create fake user
    from packages.db.models.candidate import User

    user = User(id=user_id, email=f"test_{user_id}@test.com", hashed_password="123")
    db_session.add(user)
    db_session.commit()

    doc = Document(
        id=doc_id,
        user_id=user_id,
        filename="test.pdf",
        storage_key=f"test/{doc_id}.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="xyz123",
        status="PROCESSED",
    )
    db_session.add(doc)
    db_session.commit()

    # Run task - should skip and return immediately without errors or fetching
    with patch("packages.db.session.SessionLocal", return_value=db_session):
        with patch("packages.common.storage.MinioStorageProvider") as mock_storage:
            process_document_task(str(doc_id))
            mock_storage.assert_not_called()

    # Clean up
    db_session.delete(doc)
    db_session.commit()
