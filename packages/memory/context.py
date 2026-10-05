import uuid
from typing import List, Optional

from packages.db.models.memory import MemoryFact
from packages.memory.service import MemoryService
from packages.schemas.models import CandidateContext, MemoryFactSchema


class CandidateContextBuilder:
    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service

    def build_context(
        self,
        user_id: uuid.UUID,
        query: Optional[str] = None,
        query_embedding: Optional[list[float]] = None,
    ) -> CandidateContext:
        """
        Builds a context for the candidate tailored to an application question or form field.
        """
        # 1. Stale Items
        stale_db_items = self.memory_service.check_staleness(user_id)
        stale_items = [MemoryFactSchema.model_validate(item) for item in stale_db_items]

        # 2. Conflicts
        # For this implementation, we return facts that have conflicts or need reconfirmation
        conflicts: List[MemoryFactSchema] = []

        # 3. Relevant Skills
        relevant_skills: List[MemoryFactSchema] = []
        if query or query_embedding:
            skills_db = self.memory_service.hybrid_search(
                user_id=user_id,
                query=query or "",
                category="SKILL",
                query_embedding=query_embedding,
            )
            relevant_skills = [MemoryFactSchema.model_validate(s) for s in skills_db]

        # 4. Relevant Projects
        relevant_projects: List[MemoryFactSchema] = []
        if query or query_embedding:
            projects_db = self.memory_service.hybrid_search(
                user_id=user_id,
                query=query or "",
                category="PROJECT",
                query_embedding=query_embedding,
            )
            relevant_projects = [MemoryFactSchema.model_validate(p) for p in projects_db]

        # 5. Relevant Experience
        relevant_exp: List[MemoryFactSchema] = []
        if query or query_embedding:
            exp_db = self.memory_service.hybrid_search(
                user_id=user_id,
                query=query or "",
                category="EXPERIENCE",
                query_embedding=query_embedding,
            )
            relevant_exp = [MemoryFactSchema.model_validate(e) for e in exp_db]

        # 6. Facts (Identity/Basic)
        base_facts_db = (
            self.memory_service.db.query(MemoryFact)
            .filter(
                MemoryFact.user_id == user_id,
                MemoryFact.category.in_(["IDENTITY", "LOCATION", "EDUCATION"]),
                MemoryFact.is_current,
            )
            .all()
        )
        facts = [MemoryFactSchema.model_validate(f) for f in base_facts_db]

        return CandidateContext(
            facts=facts,
            relevant_experience=relevant_exp,
            relevant_projects=relevant_projects,
            relevant_skills=relevant_skills,
            conflicts=conflicts,
            stale_items=stale_items,
        )
