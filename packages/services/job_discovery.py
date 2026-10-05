import hashlib
import re
import unicodedata
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from packages.db.models.jobs import Job, JobSourcePayload
from packages.llm.provider import LLMProvider
from packages.schemas.models import JobNormalizedSchema, JobRequirementSchema


class RequirementExtractionResponse(BaseModel):
    requirements: List[JobRequirementSchema]


class DisambiguationResponse(BaseModel):
    is_duplicate: bool
    reasoning: str


class JobDiscoveryService:
    def __init__(self, llm_provider: LLMProvider, semantic_threshold: float = 0.85):
        self.llm = llm_provider
        self.semantic_threshold = semantic_threshold

    @staticmethod
    def _normalize_text(text_in: Optional[str]) -> str:
        """Basic whitespace and case normalization."""
        if not text_in:
            return ""
        # Unicode normalization
        normalized = unicodedata.normalize("NFKC", text_in)
        return " ".join(normalized.split()).strip().lower()

    @staticmethod
    def normalize_url(url: Optional[str]) -> str:
        """Strips tracking params and normalizes URL scheme/host/path."""
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            # Remove tracking query parameters like utm_*
            if parsed.query:
                query_pairs = parsed.query.split("&")
                clean_pairs = [
                    p
                    for p in query_pairs
                    if not p.startswith("utm_") and not p.startswith("_hsenc")
                ]
                clean_query = "&".join(clean_pairs)
            else:
                clean_query = ""

            path = parsed.path.rstrip("/")

            return urlunparse(
                (
                    parsed.scheme.lower(),
                    parsed.netloc.lower(),
                    path,
                    parsed.params,
                    clean_query,
                    "",  # Strip fragments
                )
            )
        except Exception:
            return url.strip()

    @staticmethod
    def build_job_fingerprint(job: JobNormalizedSchema) -> str:
        """Deterministic cryptographic hash of canonical company, title, location, employment_type."""  # noqa: E501
        components = [
            job.canonical_company or "",
            JobDiscoveryService._normalize_text(job.title) or "",
            JobDiscoveryService._normalize_text(job.location) or "",
            JobDiscoveryService._normalize_text(job.employment_type) or "",
        ]
        fingerprint_raw = "|".join(components)
        return hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()

    @staticmethod
    def build_content_hash(description: str) -> str:
        """Strips HTML, normalizes unicode/whitespace, returns SHA-256."""
        if not description:
            return ""
        # Naive HTML strip
        no_html = re.sub(r"<[^>]+>", " ", description)
        normalized = JobDiscoveryService._normalize_text(no_html)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def normalize_job(
        self, raw_job: Dict[str, Any], source: str, source_id: uuid.UUID
    ) -> JobNormalizedSchema:
        """Normalizes a raw job from a connector into a canonical format."""
        title = raw_job.get("title", "") or raw_job.get("text", "")
        company = raw_job.get("company", "Unknown")
        description = (
            raw_job.get("content", "")
            or raw_job.get("descriptionPlain", "")
            or raw_job.get("description", "")
        )

        content_hash = self.build_content_hash(description)
        canonical_url = self.normalize_url(raw_job.get("absolute_url") or raw_job.get("hostedUrl"))

        job_schema = JobNormalizedSchema(
            id=uuid.uuid4(),
            source=source,
            source_id=source_id,
            source_job_id=str(raw_job.get("id")),
            title=title,
            company=company,
            canonical_company=self._normalize_text(company).replace(" ", ""),
            location=raw_job.get("location"),
            employment_type=raw_job.get("employment_type"),
            description=description,
            canonical_url=canonical_url,
            raw_content_hash=content_hash,
        )
        return job_schema

    def extract_requirements(
        self, normalized_job: JobNormalizedSchema
    ) -> List[JobRequirementSchema]:
        """Uses JobIntelligenceService to extract structured requirements."""
        from packages.services.job_intelligence import JobIntelligenceService

        intelligence_service = JobIntelligenceService(self.llm)
        return intelligence_service.extract_requirements(normalized_job)

    def deduplicate_job(
        self,
        session: Session,
        job: JobNormalizedSchema,
        job_embedding: Optional[List[float]] = None,
    ) -> Optional[uuid.UUID]:
        """
        5-Layer Deduplication Logic.
        Returns the existing canonical Job ID if duplicate found, else None.
        """
        fingerprint = self.build_job_fingerprint(job)
        content_hash = job.raw_content_hash

        # Layer 1: Source Identity
        existing = (
            session.query(Job)
            .filter(Job.source_id == job.source_id, Job.source_job_id == job.source_job_id)
            .first()
        )
        if existing:
            return existing.id

        # Layer 2: Canonical URL
        if job.canonical_url:
            existing = session.query(Job).filter(Job.url == job.canonical_url).first()
            if existing:
                return existing.id

        # Layer 3: Deterministic Fingerprint
        existing = session.query(Job).filter(Job.fingerprint_hash == fingerprint).first()
        if existing:
            return existing.id

        # Layer 4: Content Hash
        if content_hash:
            existing = session.query(Job).filter(Job.content_hash == content_hash).first()
            if existing:
                # To prevent cross-company false positives where two companies use identical generic JDs  # noqa: E501
                if self._normalize_text(existing.company).replace(" ", "") == job.canonical_company:
                    return existing.id

        # Layer 5: Semantic Similarity
        if job_embedding:
            # We filter by canonical_company first to avoid cross-company collision
            sql = text("""
                SELECT id, 1 - (embedding <=> cast(:embedding as vector)) as similarity 
                FROM jobs 
                WHERE embedding IS NOT NULL 
                AND LOWER(REPLACE(company, ' ', '')) = :canonical_company
                ORDER BY similarity DESC 
                LIMIT 1
            """)
            res = session.execute(
                sql, {"embedding": str(job_embedding), "canonical_company": job.canonical_company}
            ).first()
            if res and res.similarity > self.semantic_threshold:
                # Double-check location to prevent combining "SF" and "NY" roles of the same title/company  # noqa: E501
                semantic_match_id = res.id
                semantic_job = session.query(Job).filter(Job.id == semantic_match_id).first()
                if semantic_job:
                    norm_job_loc = self._normalize_text(job.location)
                    norm_exist_loc = self._normalize_text(semantic_job.location)
                    if norm_job_loc == norm_exist_loc or (not norm_job_loc and not norm_exist_loc):
                        # Final LLM Disambiguation to prevent title/seniority/requisition collisions
                        system_prompt = (
                            "You are a job deduplication assistant. Your task is to determine if two job descriptions "  # noqa: E501
                            "are for the EXACT SAME requisition. Compare company, title, location, seniority, and content. "  # noqa: E501
                            "Return true ONLY if they are the exact same job. If one is 'Senior' and another is not, return false. "  # noqa: E501
                            "If they represent different requisitions for the same role, return false."  # noqa: E501
                        )
                        prompt = (
                            f"JOB 1:\nTitle: {semantic_job.title}\nCompany: {semantic_job.company}\n"  # noqa: E501
                            f"Location: {semantic_job.location}\nContent: {semantic_job.description}\n\n"  # noqa: E501
                            f"JOB 2:\nTitle: {job.title}\nCompany: {job.company}\n"
                            f"Location: {job.location}\nContent: {job.description}\n"
                        )
                        disambiguation = self.llm.generate_structured(
                            prompt, DisambiguationResponse, system_prompt=system_prompt
                        )
                        if disambiguation.is_duplicate:
                            return semantic_job.id

        return None

    def process_discovered_job(
        self,
        session: Session,
        raw_job: Dict[str, Any],
        source: str,
        source_id: uuid.UUID,
        job_embedding: Optional[List[float]] = None,
    ) -> Job:
        """
        Orchestrates normalization, deduplication, and database persistence while preserving provenance.
        """  # noqa: E501
        normalized = self.normalize_job(raw_job, source, source_id)
        dup_id = self.deduplicate_job(session, normalized, job_embedding)

        # Deterministic representation of raw dict for hash
        payload_hash = hashlib.sha256(str(sorted(raw_job.items())).encode("utf-8")).hexdigest()

        if dup_id:
            canonical_job = session.query(Job).filter(Job.id == dup_id).first()
        else:
            canonical_job = Job(
                id=normalized.id,
                source_id=source_id,
                source_job_id=normalized.source_job_id,
                title=normalized.title,
                company=normalized.company,
                location=normalized.location,
                employment_type=normalized.employment_type,
                description=normalized.description,
                url=normalized.canonical_url,
                fingerprint_hash=self.build_job_fingerprint(normalized),
                content_hash=normalized.raw_content_hash,
            )
            session.add(canonical_job)

        # Save provenance payload linked to canonical job
        # Avoid duplicate payload insertion if already exists (idempotency)
        existing_payload = (
            session.query(JobSourcePayload)
            .filter(
                JobSourcePayload.source_id == source_id,
                JobSourcePayload.source_job_id == normalized.source_job_id,
            )
            .first()
        )

        if not existing_payload:
            payload = JobSourcePayload(
                canonical_job_id=canonical_job.id,  # type: ignore[union-attr]
                source_id=source_id,
                source_job_id=normalized.source_job_id,
                payload_hash=payload_hash,
                raw_payload=raw_job,
            )
            session.add(payload)

        return canonical_job  # type: ignore[return-value]
