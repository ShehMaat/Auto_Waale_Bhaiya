import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from packages.db.models.memory import MemoryFact
from packages.schemas.enums import MemoryProvenance, MemoryStatus, MemoryTrustLevel

if TYPE_CHECKING:
    from packages.schemas.models import MemoryQuery


class MemoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_memory_by_key(self, user_id: uuid.UUID, key: str) -> Optional[MemoryFact]:
        return (
            self.db.query(MemoryFact)
            .filter(MemoryFact.user_id == user_id, MemoryFact.key == key, MemoryFact.is_current)
            .first()
        )

    def get_memory_by_id(self, user_id: uuid.UUID, memory_id: uuid.UUID) -> Optional[MemoryFact]:
        return (
            self.db.query(MemoryFact)
            .filter(MemoryFact.id == memory_id, MemoryFact.user_id == user_id)
            .first()
        )

    def create_or_update_memory(
        self,
        user_id: uuid.UUID,
        category: str,
        key: str,
        value: str,
        trust_level: MemoryTrustLevel,
        provenance: MemoryProvenance,
        confidence: float = 1.0,
        source: Optional[str] = None,
        valid_until: Optional[datetime] = None,
        normalized_value: Optional[str] = None,
        embedding: Optional[list[float]] = None,
    ) -> Tuple[MemoryFact, bool]:
        """
        Creates or updates a memory fact.
        Returns a tuple of (MemoryFact, bool) where bool is True if a conflict was detected.
        """
        if category.upper() in [
            "PASSWORD",
            "OTP",
            "2FA",
            "SECURITY_CODE",
            "AUTHENTICATION_FIELD",
            "CAPTCHA",
        ]:
            raise ValueError(f"Credential persistence is prohibited for category: {category}")

        existing = self.get_memory_by_key(user_id, key)

        trust_hierarchy = {
            MemoryTrustLevel.GENERATED: 1,
            MemoryTrustLevel.LLM_INFERRED: 2,
            MemoryTrustLevel.SYSTEM_DERIVED: 3,
            MemoryTrustLevel.EXPLICIT_PROFILE: 4,
            MemoryTrustLevel.VERIFIED_DOCUMENT: 5,
            MemoryTrustLevel.USER_CONFIRMED: 6,
        }

        # Conflict Detection
        if existing and existing.value != value:
            existing_trust_score = trust_hierarchy.get(MemoryTrustLevel(existing.trust_level), 0)
            new_trust_score = trust_hierarchy.get(trust_level, 0)

            if new_trust_score < existing_trust_score:
                # Return existing, flag as conflict but don't override higher trust
                return existing, True

            # Create new version
            existing.is_current = False
            new_version = MemoryFact(
                user_id=user_id,
                category=category,
                key=key,
                value=value,
                normalized_value=normalized_value,
                trust_level=trust_level.value,
                provenance=provenance.value,
                confidence=confidence,
                source=source,
                status=MemoryStatus.SUGGESTED.value
                if trust_level in [MemoryTrustLevel.LLM_INFERRED, MemoryTrustLevel.GENERATED]
                else MemoryStatus.CONFIRMED.value,
                version=existing.version + 1,
                is_current=True,
                valid_from=datetime.now(timezone.utc),
                valid_until=valid_until,
                last_verified_at=datetime.now(timezone.utc),
                embedding=embedding,
            )
            self.db.add(new_version)
            self.db.commit()
            self.db.refresh(new_version)
            return new_version, False

        elif existing and existing.value == value:
            existing.last_verified_at = datetime.now(timezone.utc)
            # Promote trust if appropriate
            existing_trust_score = trust_hierarchy.get(MemoryTrustLevel(existing.trust_level), 0)
            new_trust_score = trust_hierarchy.get(trust_level, 0)
            if new_trust_score > existing_trust_score:
                existing.trust_level = trust_level.value
                existing.provenance = provenance.value
                if trust_level not in [MemoryTrustLevel.LLM_INFERRED, MemoryTrustLevel.GENERATED]:
                    existing.status = MemoryStatus.CONFIRMED.value

            if embedding is not None:
                existing.embedding = embedding

            self.db.commit()
            self.db.refresh(existing)
            return existing, False

        new_fact = MemoryFact(
            user_id=user_id,
            category=category,
            key=key,
            value=value,
            normalized_value=normalized_value,
            trust_level=trust_level.value,
            provenance=provenance.value,
            confidence=confidence,
            source=source,
            status=MemoryStatus.SUGGESTED.value
            if trust_level in [MemoryTrustLevel.LLM_INFERRED, MemoryTrustLevel.GENERATED]
            else MemoryStatus.CONFIRMED.value,
            version=1,
            is_current=True,
            valid_from=datetime.now(timezone.utc),
            valid_until=valid_until,
            last_verified_at=datetime.now(timezone.utc),
            embedding=embedding,
        )
        self.db.add(new_fact)
        self.db.commit()
        self.db.refresh(new_fact)
        return new_fact, False

    def confirm_memory(self, user_id: uuid.UUID, memory_id: uuid.UUID) -> Optional[MemoryFact]:
        fact = self.get_memory_by_id(user_id, memory_id)
        if fact:
            fact.trust_level = MemoryTrustLevel.USER_CONFIRMED.value
            fact.status = MemoryStatus.CONFIRMED.value
            fact.last_verified_at = datetime.now(timezone.utc)
            fact.needs_reconfirmation = False
            self.db.commit()
            self.db.refresh(fact)
        return fact

    def invalidate_memory(self, user_id: uuid.UUID, memory_id: uuid.UUID) -> Optional[MemoryFact]:
        fact = self.get_memory_by_id(user_id, memory_id)
        if fact:
            fact.status = MemoryStatus.REJECTED.value
            fact.is_current = False
            self.db.commit()
            self.db.refresh(fact)
        return fact

    def check_staleness(self, user_id: uuid.UUID) -> List[MemoryFact]:
        now = datetime.now(timezone.utc)
        stale_facts = (
            self.db.query(MemoryFact)
            .filter(
                MemoryFact.user_id == user_id,
                MemoryFact.is_current,
                MemoryFact.valid_until.is_not(None),
                MemoryFact.valid_until < now,
                MemoryFact.needs_reconfirmation.is_(False),
            )
            .all()
        )
        for fact in stale_facts:
            fact.needs_reconfirmation = True
        self.db.commit()
        return stale_facts

    def hybrid_search(
        self,
        user_id: uuid.UUID,
        query: str,
        category: Optional[str] = None,
        min_confidence: float = 0.5,
        min_trust: Optional[MemoryTrustLevel] = None,
        top_k: int = 5,
        query_embedding: Optional[list[float]] = None,
    ) -> List[MemoryFact]:
        db_query = self.db.query(MemoryFact).filter(
            MemoryFact.user_id == user_id,
            MemoryFact.is_current,
            MemoryFact.confidence >= min_confidence,
            MemoryFact.status != MemoryStatus.REJECTED.value,
        )

        if category:
            db_query = db_query.filter(MemoryFact.category == category)

        if min_trust:
            trust_hierarchy = {
                MemoryTrustLevel.GENERATED: 1,
                MemoryTrustLevel.LLM_INFERRED: 2,
                MemoryTrustLevel.SYSTEM_DERIVED: 3,
                MemoryTrustLevel.EXPLICIT_PROFILE: 4,
                MemoryTrustLevel.VERIFIED_DOCUMENT: 5,
                MemoryTrustLevel.USER_CONFIRMED: 6,
            }
            min_score = trust_hierarchy.get(min_trust, 0)
            valid_trust_levels = [k.value for k, v in trust_hierarchy.items() if v >= min_score]
            db_query = db_query.filter(MemoryFact.trust_level.in_(valid_trust_levels))

        if query_embedding:
            # Semantic search ordered by l2 distance
            db_query = db_query.order_by(MemoryFact.embedding.l2_distance(query_embedding))
        else:
            # Fallback to exact match logic if no embedding
            db_query = db_query.filter(
                or_(MemoryFact.key.ilike(f"%{query}%"), MemoryFact.value.ilike(f"%{query}%"))
            )

        return db_query.limit(top_k).all()

    def get_memory_history(self, user_id: uuid.UUID, key: str) -> List[MemoryFact]:
        return (
            self.db.query(MemoryFact)
            .filter(MemoryFact.user_id == user_id, MemoryFact.key == key)
            .order_by(MemoryFact.version.desc())
            .all()
        )

    def query_memory(
        self, query: "MemoryQuery", query_embedding: Optional[list[float]] = None
    ) -> List[MemoryFact]:
        now = datetime.now(timezone.utc)
        db_query = self.db.query(MemoryFact).filter(
            MemoryFact.user_id == query.candidate_id,
            MemoryFact.status != MemoryStatus.REJECTED.value,
        )

        if not query.include_superseded:
            db_query = db_query.filter(MemoryFact.is_current)

        if not query.include_expired:
            db_query = db_query.filter(
                or_(MemoryFact.valid_until.is_(None), MemoryFact.valid_until > now)
            )

        if query.fact_types:
            db_query = db_query.filter(MemoryFact.category.in_(query.fact_types))

        if query.min_trust:
            trust_hierarchy = {
                MemoryTrustLevel.GENERATED: 1,
                MemoryTrustLevel.LLM_INFERRED: 2,
                MemoryTrustLevel.SYSTEM_DERIVED: 3,
                MemoryTrustLevel.EXPLICIT_PROFILE: 4,
                MemoryTrustLevel.VERIFIED_DOCUMENT: 5,
                MemoryTrustLevel.USER_CONFIRMED: 6,
            }
            min_score = trust_hierarchy.get(query.min_trust, 0)
            valid_trust_levels = [k.value for k, v in trust_hierarchy.items() if v >= min_score]
            db_query = db_query.filter(MemoryFact.trust_level.in_(valid_trust_levels))

        if query_embedding and self.db.bind and self.db.bind.dialect.name == "postgresql":
            db_query = db_query.order_by(MemoryFact.embedding.l2_distance(query_embedding))
        else:
            db_query = db_query.filter(
                or_(
                    MemoryFact.key.ilike(f"%{query.query_text}%"),
                    MemoryFact.value.ilike(f"%{query.query_text}%"),
                )
            )

        return db_query.limit(query.limit).all()
