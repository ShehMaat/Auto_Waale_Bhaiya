import uuid

from packages.schemas.models import JobNormalizedSchema
from packages.services.job_discovery import JobDiscoveryService


def test_normalize_url() -> None:  # type: ignore[no-untyped-def]
    url = "HTTPS://example.com/job/123/?utm_source=google&_hsenc=456&valid=1#fragment"
    norm = JobDiscoveryService.normalize_url(url)
    assert norm == "https://example.com/job/123?valid=1"


def test_build_job_fingerprint() -> None:  # type: ignore[no-untyped-def]
    job1 = JobNormalizedSchema(
        id=uuid.uuid4(),
        source="src",
        source_id=uuid.uuid4(),
        source_job_id="1",
        title=" Software Engineer ",
        company=" Apple Inc ",
        canonical_company="appleinc",
        location=" remote ",
        employment_type=" full-time ",
        description="",
        canonical_url="",
    )
    job2 = JobNormalizedSchema(
        id=uuid.uuid4(),
        source="src",
        source_id=uuid.uuid4(),
        source_job_id="2",
        title="Software Engineer",
        company="apple inc",
        canonical_company="appleinc",
        location="Remote",
        employment_type="Full-Time",
        description="",
        canonical_url="",
    )

    # Fingerprint should be identical despite casing/spacing/descriptions
    fp1 = JobDiscoveryService.build_job_fingerprint(job1)
    fp2 = JobDiscoveryService.build_job_fingerprint(job2)
    assert fp1 == fp2


def test_build_content_hash() -> None:  # type: ignore[no-untyped-def]
    desc1 = "  <p>Hello <b>World</b></p>  "
    desc2 = "\nhello \t world\n"
    # Should strip HTML and normalize whitespace identically
    h1 = JobDiscoveryService.build_content_hash(desc1)
    h2 = JobDiscoveryService.build_content_hash(desc2)
    assert h1 == h2
