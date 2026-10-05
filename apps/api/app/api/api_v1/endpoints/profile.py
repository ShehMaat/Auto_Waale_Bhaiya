from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.app.api.deps import CurrentUser, get_db
from packages.db.models.candidate import Profile
from packages.schemas.models import CandidateProfileSchema

router = APIRouter()


@router.get("", response_model=CandidateProfileSchema)
def get_profile(current_user: CurrentUser, db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]  # noqa: B008
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("", response_model=CandidateProfileSchema)
def update_profile(  # type: ignore[no-untyped-def]
    current_user: CurrentUser,
    update_data: dict,  # type: ignore[type-arg]
    db: Session = Depends(get_db),  # noqa: B008
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    for key, value in update_data.items():
        if hasattr(profile, key) and key != "id" and key != "user_id":
            setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile
