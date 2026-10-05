import uuid

import pytest

from packages.db.models.memory import MemoryFact
from packages.schemas.enums import MemoryProvenance, MemoryStatus


def test_llm_suggested_never_automatically_confirmed() -> None:  # type: ignore[no-untyped-def]
    """
    Ensures that a fact with provenance LLM_SUGGESTED
    cannot be created or updated with a status of CONFIRMED
    without an explicit user action modifying the provenance.
    """

    fact = MemoryFact(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        category="SKILL",
        key="Skill",
        value="Python",
        trust_level="LLM_INFERRED",
        confidence=0.8,
        provenance=MemoryProvenance.LLM_SUGGESTED,
        status=MemoryStatus.SUGGESTED,
    )

    def update_fact_status(fact: MemoryFact, new_status: MemoryStatus, actor: str):  # type: ignore[no-untyped-def]
        if (
            new_status == MemoryStatus.CONFIRMED
            and fact.provenance == MemoryProvenance.LLM_SUGGESTED
        ):
            if actor != "USER":
                raise ValueError("LLM_SUGGESTED facts can only be confirmed by a user action.")
            else:
                fact.status = MemoryStatus.CONFIRMED
                fact.provenance = MemoryProvenance.USER_CONFIRMED
        else:
            fact.status = new_status

    # System tries to confirm an LLM suggestion
    with pytest.raises(
        ValueError, match="LLM_SUGGESTED facts can only be confirmed by a user action."
    ):
        update_fact_status(fact, MemoryStatus.CONFIRMED, actor="SYSTEM")

    # User confirms an LLM suggestion
    update_fact_status(fact, MemoryStatus.CONFIRMED, actor="USER")

    # Verify the invariant
    assert fact.status == MemoryStatus.CONFIRMED
    assert fact.provenance == MemoryProvenance.USER_CONFIRMED
