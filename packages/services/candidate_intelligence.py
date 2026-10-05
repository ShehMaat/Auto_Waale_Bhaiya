import uuid
from typing import List, Optional

from pydantic import BaseModel

from packages.db.models.memory import MemoryFact
from packages.llm.provider import LLMProvider
from packages.schemas.enums import MemoryProvenance, MemoryStatus


class ExtractedFact(BaseModel):
    category: str
    content: str
    confidence: float
    evidence: Optional[str] = None


class CandidateIntelligenceService:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    def extract_resume_facts(
        self, resume_text: str, user_id: uuid.UUID, source_filename: str
    ) -> List[MemoryFact]:
        system_prompt = (
            "You are an expert resume parser. Extract structured facts from the resume text provided. "  # noqa: E501
            "Categories MUST be one of: SKILL, EXPERIENCE, EDUCATION, PROJECT, CERTIFICATION, PREFERENCE. "  # noqa: E501
            "Keep content concise and atomic. Include evidence for each fact."
        )

        class FactList(BaseModel):
            facts: List[ExtractedFact]

        result = self.llm.generate_structured(resume_text, FactList, system_prompt=system_prompt)

        memory_facts = []
        for fact in result.facts:
            memory_facts.append(
                MemoryFact(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    category=fact.category.upper(),
                    value=fact.content,
                    confidence=fact.confidence,
                    provenance=MemoryProvenance.RESUME_EXTRACTED,
                    status=MemoryStatus.SUGGESTED,
                    source=source_filename,
                )
            )

        return memory_facts

    def generate_candidate_embedding(self, facts: List[MemoryFact]) -> List[float]:
        """Combines confirmed facts and generates a profile embedding."""
        canonical_text = "\n".join(
            [f"{f.category}: {f.value}" for f in facts if f.status == MemoryStatus.CONFIRMED]
        )
        if not canonical_text:
            return [0.0] * 1536  # Default if empty
        return self.llm.embed(canonical_text)
