from typing import List

from pydantic import BaseModel


class NormalizedSkill(BaseModel):
    raw_name: str
    canonical_name: str
    category: str = "SKILL"


class SkillNormalizationService:
    def __init__(self) -> None:
        # Static mapping for Phase 4
        self._mapping = {
            "postgres": "POSTGRESQL",
            "postgresql": "POSTGRESQL",
            "postgres db": "POSTGRESQL",
            "pytorch": "PYTORCH",
            "torch": "PYTORCH",
            "scikit-learn": "SCIKIT_LEARN",
            "sklearn": "SCIKIT_LEARN",
            "scikit learn": "SCIKIT_LEARN",
            "js": "JAVASCRIPT",
            "javascript": "JAVASCRIPT",
            "ts": "TYPESCRIPT",
            "typescript": "TYPESCRIPT",
            "reactjs": "REACT",
            "react.js": "REACT",
            "react": "REACT",
            "node.js": "NODEJS",
            "nodejs": "NODEJS",
            "node": "NODEJS",
            "aws": "AWS",
            "amazon web services": "AWS",
            "python": "PYTHON",
            "python3": "PYTHON",
        }

    def normalize_skill(self, raw_skill: str) -> NormalizedSkill:
        """Normalizes a single skill."""
        clean = raw_skill.lower().strip()
        canonical = self._mapping.get(clean, clean.upper())
        return NormalizedSkill(raw_name=raw_skill, canonical_name=canonical)

    def normalize_skills(self, raw_skills: List[str]) -> List[NormalizedSkill]:
        """Normalizes a list of skills."""
        return [self.normalize_skill(s) for s in raw_skills]
