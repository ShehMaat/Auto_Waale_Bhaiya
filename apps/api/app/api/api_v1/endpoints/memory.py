import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.app.api.deps import CurrentUser, get_db
from packages.db.models.memory import MemoryFact
from packages.schemas.enums import MemoryStatus
from packages.schemas.models import MemoryFactSchema

router = APIRouter()


@router.get("", response_model=List[MemoryFactSchema])
def list_memory_facts(current_user: CurrentUser, db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]  # noqa: B008
    """List all candidate memory facts."""
    return db.query(MemoryFact).filter(MemoryFact.user_id == current_user.id).all()


@router.patch("/{id}/verify")
def verify_memory_fact(
    id: uuid.UUID,
    current_user: CurrentUser,
    confirm: bool,
    db: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """User verification of a memory fact."""
    fact = (
        db.query(MemoryFact)
        .filter(MemoryFact.id == id, MemoryFact.user_id == current_user.id)
        .first()
    )
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")

    if confirm:
        fact.status = MemoryStatus.CONFIRMED
    else:
        fact.status = MemoryStatus.REJECTED

    db.commit()
    return {"message": "Fact updated successfully"}
