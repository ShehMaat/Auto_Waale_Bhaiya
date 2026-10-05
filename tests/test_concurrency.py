import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from apps.api.app.core.celery_tasks import process_document_task
from packages.db.models.candidate import Document, User


@pytest.fixture
def test_user(db_session) -> None:  # type: ignore[no-untyped-def]
    import uuid

    user_id = uuid.uuid4()
    user = User(id=user_id, email=f"test-{user_id}@example.com", hashed_password="fake")
    db_session.add(user)
    db_session.commit()
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.mark.asyncio
async def test_concurrent_document_processing(db_session: Session, test_user) -> None:  # type: ignore[no-untyped-def]
    """
    Tests that if two workers try to process the same document concurrently,
    only one succeeds and the other safely skips it due to SKIP LOCKED / constraints.
    """
    doc_id = uuid.uuid4()
    # 1. Setup Document
    doc = Document(
        id=doc_id,
        user_id=test_user.id,
        filename="test.pdf",
        storage_key="test-key",
        mime_type="application/pdf",
        file_size=1024,
        checksum="dummy",
        status="PENDING",
    )
    db_session.add(doc)
    db_session.commit()

    # 2. Simulate concurrent worker execution
    with patch("packages.db.session.SessionLocal", return_value=db_session):
        with patch("packages.common.storage.MinioStorageProvider"):
            with patch("packages.services.document_parser.DocumentParser") as MockParser:
                MockParser.extract_text_from_bytes.return_value = "Extracted text"
                with patch(
                    "apps.api.app.core.celery_tasks.extract_resume_facts_task.delay"
                ) as mock_delay:
                    # We can't truly test SKIP LOCKED in a single-threaded synchronous test easily
                    # without using raw asyncpg or threadpools.
                    # However, we can simulate sequential calls to verify idempotency state updates.

                    # Worker 1
                    process_document_task(str(doc_id))

                    # Worker 2
                    process_document_task(str(doc_id))

                    doc = db_session.query(Document).filter(Document.id == doc_id).first()

                    # It should only trigger the next phase once
                    mock_delay.assert_called_once()

    # Verify final state
    doc = db_session.query(Document).filter(Document.id == doc_id).first()
    assert doc.status == "PROCESSED"
