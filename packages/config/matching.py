from pydantic import BaseModel


class MatchingConfig(BaseModel):
    semantic_match_threshold: float = 0.85
    partial_match_threshold: float = 0.70
    semantic_weight: float = 0.30
    skill_weight: float = 0.30
    experience_weight: float = 0.20
    education_weight: float = 0.10
    preference_weight: float = 0.10
    config_version: str = "v1.0"
