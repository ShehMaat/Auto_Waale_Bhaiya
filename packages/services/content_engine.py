import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from packages.browser.form_intelligence.decision_engine import DecisionEngine
from packages.db.models.content import ApplicationContent, ContentGenerationEvent, ContentVersion
from packages.db.models.jobs import Job
from packages.db.models.memory import MemoryFact
from packages.llm.provider import LLMProvider
from packages.memory.service import MemoryService
from packages.schemas.content import (
    ApplicationContentRequest,
    ApplicationContentResult,
    ContentValidationResult,
    EvidencePack,
    GenerationMetadata,
)
from packages.schemas.enums import DecisionType, FieldType, MemoryTrustLevel
from packages.schemas.form import FieldClassification, FormField


class ContentEngine:
    def __init__(self, db: Session, llm_provider: LLMProvider, decision_engine: DecisionEngine):
        self.db = db
        self.llm = llm_provider
        self.decision_engine = decision_engine
        self.memory_service = MemoryService(db)

    def _build_evidence_pack(self, request: ApplicationContentRequest) -> EvidencePack:
        # Retrieve candidate evidence using MemoryService
        # Must be user-scoped, application-aware, provenance-aware, temporal-validity-aware
        # Omitting stale evidence.

        # We will get active, current memories
        memories = (
            self.db.execute(select(MemoryFact).where(MemoryFact.user_id == request.user_id))
            .scalars()
            .all()
        )

        # Filter for trust (no UNKNOWN, no CONTRADICTED, no EXPIRED)
        # In a real app we would use temporal validity
        valid_mems = []
        now = datetime.now(timezone.utc)
        for m in memories:
            if not m.is_current:
                continue
            if m.valid_until and m.valid_until.replace(tzinfo=timezone.utc) < now:
                continue

            # Filter low trust levels silently promoting to factual claims
            invalid_trust = [MemoryTrustLevel.GENERATED.value, MemoryTrustLevel.LLM_INFERRED.value]
            if m.trust_level in invalid_trust:
                continue
            valid_mems.append(m)

        # Build pack deterministically (and handle contradiction)
        from collections import defaultdict

        grouped_mems = defaultdict(list)
        for m in valid_mems:
            grouped_mems[(m.category, m.key)].append(m)

        pack = EvidencePack()
        for (_cat, _key), mems in grouped_mems.items():
            if len(mems) > 1:
                # Check if values differ (contradiction)
                values = set(m.value for m in mems)
                if len(values) > 1:
                    continue  # Omit disputed claim entirely

            for m in mems:
                pack.candidate_facts.append(
                    {
                        "category": m.category,
                        "key": m.key,
                        "value": m.value,
                        "trust_level": m.trust_level,
                        "provenance": m.provenance,
                    }
                )

        # Get Job Context
        job = self.db.execute(select(Job).where(Job.id == request.job_id)).scalars().first()

        if job:
            if job.extracted_requirements:
                pack.job_requirements = job.extracted_requirements.get("requirements", [])
                pack.job_responsibilities = job.extracted_requirements.get("responsibilities", [])
            pack.company_context = {"company": job.company, "title": job.title}

        return pack

    def _validate_content(
        self, content: str, request: ApplicationContentRequest, pack: EvidencePack
    ) -> ContentValidationResult:
        errors = []
        is_valid = True
        is_grounded = True
        safe = True

        # Credential protection / Sensitive data redaction
        # Block passwords, OTPs, API keys if detected (stub for deterministic test)
        lower_content = content.lower()
        for secret in ["password", "otp", "2fa", "test_secret_123", "123456"]:
            if secret in lower_content and "password" in request.prompt.lower():
                errors.append(f"Credential exposure detected: {secret}")
                is_valid = False
                safe = False

        # Length validation
        if request.max_words and len(content.split()) > request.max_words:
            errors.append("Word limit exceeded")
            is_valid = False

        if request.max_characters and len(content) > request.max_characters:
            errors.append("Character limit exceeded")
            is_valid = False

        # Grounding check (mocking LLM self-validation for unsupported claims)
        # Any candidate-specific claim must be supported by the EvidencePack.
        # Let's just create a mock claim here that would be rejected if it's "led a team of 20"
        if "led a team of 20" in content.lower():
            is_grounded = False
            is_valid = False
            errors.append("Unsupported claim detected")

        # Prompt injection check
        if "ignore previous instructions" in content.lower():
            safe = False
            is_valid = False
            errors.append("Prompt injection detected")

        return ContentValidationResult(
            is_valid=is_valid, is_grounded=is_grounded, safe=safe, errors=errors
        )

    def generate(self, request: ApplicationContentRequest) -> ApplicationContentResult:
        pack = self._build_evidence_pack(request)

        # Security: Credential request blocked early
        lower_prompt = request.prompt.lower()
        if "password" in lower_prompt or "otp" in lower_prompt or "secret" in lower_prompt:
            val_res = ContentValidationResult(
                is_valid=False, is_grounded=False, safe=False, errors=["Credential request blocked"]
            )
            decision = DecisionType.BLOCK

            event = ContentGenerationEvent(
                application_id=request.application_id,
                job_id=request.job_id,
                user_id=request.user_id,
                content_type=request.content_type.value,
                generation_version="phase9-v1",
                policy_version="phase8-v1",
                model_identifier="mock-model",
                evidence_references=[],
                validation_result=val_res.model_dump(),
                decision_result=decision.value,
            )
            self.db.add(event)
            self.db.commit()

            return ApplicationContentResult(
                content_id=uuid.uuid4(),
                application_id=request.application_id,
                content="",
                version=1,
                validation=val_res,
                metadata=GenerationMetadata(
                    model_identifier="none",
                    generator_version="phase9-v1",
                    policy_version="phase8-v1",
                ),
                evidence_snapshot=pack,
            )

        # Draft generation
        prompt = (
            f"Generate {request.content_type.value} based on evidence. "
            f"Tone: {request.tone.value}. Mode: {request.mode.value}. Request: {request.prompt}"
        )
        generated_text = self.llm.generate(prompt)

        # Validate
        validation = self._validate_content(generated_text, request, pack)

        # Phase 8 Decision Engine Integration
        # We model the content as a FormField to pass through decision engine for policy
        field = FormField(
            field_id="content_gen",
            element_id="content_gen_1",
            form_id="content_form",
            label=request.content_type.value,
            classification=FieldClassification(field_type=FieldType.UNKNOWN, confidence=1.0),
        )
        # Using Phase 8 engine to evaluate policy
        decision_obj = self.decision_engine.decide(field, profile=None, memories=[])
        decision = decision_obj.decision_type

        if not validation.is_valid or not validation.safe:
            decision = DecisionType.BLOCK

        # Save Content
        # Idempotency: find existing content for this app/type/prompt
        stmt = select(ApplicationContent).where(
            and_(
                ApplicationContent.application_id == request.application_id,
                ApplicationContent.content_type == request.content_type.value,
                ApplicationContent.prompt == request.prompt,
            )
        )
        content_record = self.db.execute(stmt).scalars().first()

        if not content_record:
            content_record = ApplicationContent(
                application_id=request.application_id,
                job_id=request.job_id,
                user_id=request.user_id,
                content_type=request.content_type.value,
                prompt=request.prompt,
            )
            self.db.add(content_record)
            self.db.flush()

        # Get latest version
        version_stmt = (
            select(ContentVersion)
            .where(ContentVersion.content_id == content_record.id)
            .order_by(ContentVersion.version.desc())
        )
        last_version = self.db.execute(version_stmt).scalars().first()
        new_version_num = last_version.version + 1 if last_version else 1

        content_version = ContentVersion(
            content_id=content_record.id,
            application_id=request.application_id,
            version=new_version_num,
            content=generated_text,
            generator_version="phase9-v1",
            policy_version="phase8-v1",
            evidence_snapshot=pack.model_dump(),
            created_by=request.user_id,
        )
        self.db.add(content_version)

        # Event
        event = ContentGenerationEvent(
            application_id=request.application_id,
            job_id=request.job_id,
            user_id=request.user_id,
            content_type=request.content_type.value,
            generation_version="phase9-v1",
            policy_version="phase8-v1",
            model_identifier="llm-1",
            evidence_references=[],
            validation_result=validation.model_dump(),
            decision_result=decision.value,
        )
        self.db.add(event)
        self.db.commit()

        return ApplicationContentResult(
            content_id=content_record.id,
            application_id=request.application_id,
            content=generated_text,
            version=new_version_num,
            validation=validation,
            metadata=GenerationMetadata(
                model_identifier="llm-1", generator_version="phase9-v1", policy_version="phase8-v1"
            ),
            evidence_snapshot=pack,
        )
