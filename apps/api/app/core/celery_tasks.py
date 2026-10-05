import logging

from apps.api.app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="document.process_document")  # type: ignore[untyped-decorator]
def process_document_task(document_id: str) -> None:
    """Processes an uploaded document."""
    logger.info(f"Processing document {document_id}")
    import os
    import tempfile

    from packages.common.storage import MinioStorageProvider
    from packages.db.models.candidate import Document
    from packages.db.session import SessionLocal
    from packages.services.document_parser import DocumentParser

    db = SessionLocal()
    try:
        import uuid

        doc_uuid = uuid.UUID(document_id)
        # Use SKIP LOCKED to prevent concurrent processing of the same document
        doc = (
            db.query(Document)
            .filter(Document.id == doc_uuid, Document.status == "PENDING")
            .with_for_update(skip_locked=True)
            .first()
        )

        if not doc:
            logger.info(
                f"Document {document_id} not found, already processed, or locked by another worker."
            )
            return

        # IDEMPOTENCY CHECK
        if doc.status == "PROCESSED":
            logger.info(
                f"Document {document_id} is already processed. Skipping duplicate execution."
            )
            return

        storage = MinioStorageProvider()  # type: ignore[no-untyped-call]
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        success = storage.download_file(doc.storage_key, tmp_path)
        if not success:
            logger.error(f"Failed to download {doc.storage_key}")
            doc.status = "FAILED"
            db.commit()
            return

        with open(tmp_path, "rb") as f:
            file_bytes = f.read()

        text = DocumentParser.extract_text_from_bytes(file_bytes, doc.mime_type)
        os.unlink(tmp_path)

        doc.status = "PROCESSED"
        db.commit()

        # Trigger fact extraction
        extract_resume_facts_task.delay(document_id, text)

    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        doc.status = "FAILED"  # type: ignore[union-attr]
        db.commit()
    finally:
        db.close()


@celery_app.task(name="document.extract_resume_facts")  # type: ignore[untyped-decorator]
def extract_resume_facts_task(document_id: str, text: str) -> None:
    """Extracts facts from resume text using LLM."""
    logger.info(f"Extracting facts for document {document_id}")
    from packages.db.models.candidate import Document
    from packages.db.models.memory import MemoryFact
    from packages.db.session import SessionLocal
    from packages.llm.openai_provider import OpenAIProvider  # using openai as default
    from packages.schemas.enums import MemoryProvenance
    from packages.services.candidate_intelligence import CandidateIntelligenceService

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        # IDEMPOTENCY CHECK: If facts from this exact document already exist, skip execution.
        existing_facts = (
            db.query(MemoryFact)
            .filter(
                MemoryFact.user_id == doc.user_id,
                MemoryFact.source == str(doc.id),
                MemoryFact.provenance == MemoryProvenance.RESUME_EXTRACTED.value,
            )
            .first()
        )

        if existing_facts:
            logger.info(
                f"Facts already extracted for document {document_id}. Skipping duplicate execution."
            )
            return

        import hashlib

        from sqlalchemy.exc import IntegrityError

        llm = OpenAIProvider()
        service = CandidateIntelligenceService(llm)
        facts = service.extract_resume_facts(
            text, doc.user_id, str(doc.id)
        )  # Use document ID as source to guarantee uniqueness

        inserted_count = 0
        for fact in facts:
            if not getattr(fact, "content_hash", None):
                fact.content_hash = hashlib.sha256(fact.value.encode("utf-8")).hexdigest()
            try:
                db.add(fact)
                db.commit()
                inserted_count += 1
            except IntegrityError:
                db.rollback()
                logger.debug(f"Fact {fact.content_hash} already exists. Skipping.")

        logger.info(f"Extracted {inserted_count} new facts for user {doc.user_id}")
    except Exception as e:
        logger.error(f"Fact extraction failed: {e}")
    finally:
        db.close()


@celery_app.task(name="embeddings.generate_candidate_embedding")  # type: ignore[untyped-decorator]
def generate_candidate_embedding_task(user_id: str) -> None:
    """Generates embedding for canonical profile."""
    from packages.db.models.memory import MemoryFact
    from packages.db.session import SessionLocal
    from packages.llm.openai_provider import OpenAIProvider
    from packages.schemas.enums import MemoryStatus
    from packages.services.candidate_intelligence import CandidateIntelligenceService

    db = SessionLocal()
    try:
        facts = (
            db.query(MemoryFact)
            .filter(
                MemoryFact.user_id == user_id, MemoryFact.status == MemoryStatus.CONFIRMED.value
            )
            .all()
        )

        service = CandidateIntelligenceService(OpenAIProvider())
        embedding = service.generate_candidate_embedding(facts)

        # Update embedding for all confirmed facts for now (or store on profile if we add a vector there)  # noqa: E501
        # Note: The prompt asks for Candidate Embeddings. We will store it in the MemoryFacts for simplicity  # noqa: E501
        # or we could add a `vector` to `Profile`. In Phase 1 schema, MemoryFact has `embedding`.
        for fact in facts:
            fact.embedding = embedding

        db.commit()
        logger.info(f"Generated embedding for user {user_id}")
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
    finally:
        db.close()


@celery_app.task(name="job_discovery.discover_jobs")  # type: ignore[untyped-decorator]
def discover_jobs_task(source_id: str) -> None:
    """Discovers jobs from a source and persists raw payloads."""
    from sqlalchemy.exc import IntegrityError

    from packages.db.models.jobs import JobSource
    from packages.db.session import SessionLocal
    from packages.llm.openai_provider import OpenAIProvider
    from packages.services.job_discovery import JobDiscoveryService

    db = SessionLocal()
    try:
        source = db.query(JobSource).filter(JobSource.id == source_id).first()
        if not source:
            logger.error(f"Source {source_id} not found.")
            return

        # In a real scenario, this would use a connector factory
        # For Phase 2, we simulate fetching raw jobs
        from typing import Any

        raw_jobs: list[dict[str, Any]] = []

        service = JobDiscoveryService(OpenAIProvider())
        for raw_job in raw_jobs:
            try:
                canonical_job = service.process_discovered_job(db, raw_job, source.name, source.id)
                db.commit()
                # Enqueue requirements extraction
                extract_job_requirements_task.delay(str(canonical_job.id))
            except IntegrityError:
                db.rollback()
                logger.info(f"Duplicate job payload for source {source_id}. Skipping.")
    except Exception as e:
        logger.error(f"Discover jobs failed: {e}")
    finally:
        db.close()


@celery_app.task(name="job_discovery.normalize_jobs")  # type: ignore[untyped-decorator]
def normalize_jobs_task(job_id: str) -> None:
    """Standalone normalization task for reprocessing."""
    from packages.db.models.jobs import Job, JobSourcePayload
    from packages.db.session import SessionLocal
    from packages.llm.openai_provider import OpenAIProvider
    from packages.services.job_discovery import JobDiscoveryService

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        payload = (
            db.query(JobSourcePayload).filter(JobSourcePayload.canonical_job_id == job.id).first()
        )
        if not payload:
            return

        service = JobDiscoveryService(OpenAIProvider())
        normalized = service.normalize_job(payload.raw_payload, "re-normalize", payload.source_id)

        job.title = normalized.title
        job.company = normalized.company
        job.location = normalized.location
        db.commit()
    except Exception as e:
        logger.error(f"Normalize jobs failed: {e}")
    finally:
        db.close()


@celery_app.task(name="job_discovery.extract_job_requirements")  # type: ignore[untyped-decorator]
def extract_job_requirements_task(job_id: str) -> None:
    """Extracts typed requirements from a job description."""
    from packages.db.models.jobs import Job
    from packages.db.session import SessionLocal
    from packages.llm.openai_provider import OpenAIProvider
    from packages.services.job_discovery import JobDiscoveryService

    db = SessionLocal()
    try:
        # Prevent concurrent extraction using SKIP LOCKED
        job = db.query(Job).filter(Job.id == job_id).with_for_update(skip_locked=True).first()
        if not job:
            return

        if job.extracted_requirements and job.extracted_requirements.get("status") == "PROCESSED":
            return

        service = JobDiscoveryService(OpenAIProvider())
        requirements = service.extract_requirements(job.description)  # type: ignore[arg-type]

        req_dicts = [req.model_dump() for req in requirements]
        job.extracted_requirements = {"status": "PROCESSED", "requirements": req_dicts}
        db.commit()
    except Exception as e:
        logger.error(f"Extract job requirements failed: {e}")
    finally:
        db.close()


@celery_app.task(name="workflow.run_application_workflow")  # type: ignore[untyped-decorator]
def run_application_workflow_task(application_id: str) -> None:
    """Executes the Phase 3D application workflow orchestration."""
    from packages.application.workflow.orchestrator import ApplicationWorkflowOrchestrator

    try:
        logger.info(f"Starting workflow orchestration for {application_id}")
        orchestrator = ApplicationWorkflowOrchestrator(application_id)
        result = orchestrator.run_sync()
        if result.get("status") == "LOCKED":
            logger.warning(f"Workflow {application_id} locked by another worker")
    except Exception as e:
        logger.error(f"Application Workflow task failed for {application_id}: {e}")
