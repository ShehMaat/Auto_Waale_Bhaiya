import uuid

from packages.db.models.jobs import Job
from packages.llm.openai_provider import OpenAIProvider
from packages.schemas.models import JobNormalizedSchema
from packages.services.job_discovery import JobDiscoveryService


def test_deduplication_exact_source(db_session) -> None:  # type: ignore[no-untyped-def]
    service = JobDiscoveryService(OpenAIProvider())

    src_id = uuid.uuid4()
    from packages.db.models.jobs import JobSource

    js = JobSource(id=src_id, name="Test Source", source_type="BOARD", base_url="http://test.com")
    db_session.add(js)
    db_session.commit()

    # Clean up previous tests
    db_session.query(Job).filter(Job.source_id == src_id).delete()
    db_session.commit()

    # Insert existing
    existing = Job(
        id=uuid.uuid4(),
        source_id=src_id,
        source_job_id="123",
        title="Test",
        company="Test",
        description="desc",
        url="http://test.com",
    )
    db_session.add(existing)
    db_session.commit()

    # Test duplicate by source identity
    job = JobNormalizedSchema(
        id=uuid.uuid4(),
        source="board",
        source_id=src_id,
        source_job_id="123",
        title="Diff Title",
        company="Diff",
        canonical_company="diff",
        description="desc",
        canonical_url="",
    )
    dup_id = service.deduplicate_job(db_session, job)
    assert dup_id == existing.id


def test_deduplication_fingerprint(db_session) -> None:  # type: ignore[no-untyped-def]
    from packages.db.models.jobs import Job, JobSource, JobSourcePayload

    db_session.query(JobSourcePayload).delete()
    db_session.query(Job).delete()
    db_session.query(JobSource).delete()
    db_session.commit()

    service = JobDiscoveryService(OpenAIProvider())

    src_id = uuid.uuid4()
    from packages.db.models.jobs import JobSource

    js = JobSource(id=src_id, name="Apple Source", source_type="BOARD", base_url="http://apple.com")
    db_session.add(js)
    db_session.commit()

    # Insert existing
    mock_job = JobNormalizedSchema(
        id=uuid.uuid4(),
        source="src",
        source_id=uuid.uuid4(),
        source_job_id="999",
        title="Software Engineer",
        company="apple",
        canonical_company="apple",
        description="desc",
        location="remote",
        employment_type="full time",
        canonical_url="",
    )
    existing = Job(
        id=uuid.uuid4(),
        source_id=src_id,
        source_job_id="999",
        title="Software Engineer",
        company="apple",
        description="desc",
        location="remote",
        url="http://test2.com",
        fingerprint_hash=service.build_job_fingerprint(mock_job),
    )
    db_session.add(existing)
    db_session.commit()

    # Same fingerprint, different source/url
    job = JobNormalizedSchema(
        id=uuid.uuid4(),
        source="board2",
        source_id=uuid.uuid4(),
        source_job_id="123",
        title="Software Engineer",
        company="apple",
        canonical_company="apple",
        description="different desc",
        location="remote",
        employment_type="full time",
        canonical_url="",
    )
    dup_id = service.deduplicate_job(db_session, job)
    assert dup_id == existing.id
