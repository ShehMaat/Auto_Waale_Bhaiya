import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from apps.api.app.api.deps import CurrentUser, get_db
from packages.common.storage import MinioStorageProvider
from packages.db.models.candidate import Document
from packages.services.document_parser import DocumentParser

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("")
async def upload_document(  # type: ignore[no-untyped-def]
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    file: UploadFile = File(...),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Uploads a document (PDF/DOCX), stores it, and triggers processing."""
    if not file.filename.lower().endswith((".pdf", ".docx")):  # type: ignore[union-attr]
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")

    file_hash = DocumentParser.compute_hash(file_bytes)

    # Check deduplication
    existing_doc = (
        db.query(Document)
        .filter(Document.user_id == current_user.id, Document.checksum == file_hash)
        .first()
    )

    if existing_doc:
        return {"message": "Document already exists", "document_id": existing_doc.id}

    storage_key = f"users/{current_user.id}/documents/{uuid.uuid4()}_{file.filename}"

    # Upload to MinIO
    storage = MinioStorageProvider()  # type: ignore[no-untyped-call]

    # Needs a temp file approach or boto3 put_object directly for bytes
    # But MinioStorageProvider has upload_file which takes a path.
    # For now we'll write temp file and upload (this is just the API logic).
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    success = storage.upload_file(tmp_path, storage_key)
    os.unlink(tmp_path)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload document to storage.")

    # Create DB record
    doc = Document(
        user_id=current_user.id,
        filename=file.filename,
        storage_key=storage_key,
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(file_bytes),
        checksum=file_hash,
        status="PENDING",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Enqueue processing (Phase 2 celery logic to be added)
    from apps.api.app.core.celery_tasks import process_document_task

    process_document_task.delay(str(doc.id))

    return {"message": "Document uploaded successfully", "document_id": doc.id}


@router.get("")
def list_documents(current_user: CurrentUser, db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]  # noqa: B008
    """List user documents."""
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    return {"documents": docs}
