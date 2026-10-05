import math
from typing import List, Literal, Optional

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from packages.config.matching import MatchingConfig


class SemanticMatchResult(BaseModel):
    similarity_score: float
    threshold: float
    result: Literal["MATCH", "PARTIAL_MATCH", "NO_MATCH", "UNKNOWN"]
    evidence: str
    embedding_model: str
    embedding_version: str


class SemanticSimilarityEngine:
    def __init__(self, session: Session, config: MatchingConfig):
        self.session = session
        self.config = config

    def calculate_similarity(
        self,
        job_embedding: Optional[List[float]],
        candidate_embedding: Optional[List[float]],
        embedding_model: str,
        embedding_version: str,
    ) -> SemanticMatchResult:
        if not job_embedding or not candidate_embedding:
            return SemanticMatchResult(
                similarity_score=0.0,
                threshold=self.config.semantic_match_threshold,
                result="UNKNOWN",
                evidence="Missing embeddings for semantic comparison.",
                embedding_model=embedding_model,
                embedding_version=embedding_version,
            )

        if len(job_embedding) != len(candidate_embedding):
            return SemanticMatchResult(
                similarity_score=0.0,
                threshold=self.config.semantic_match_threshold,
                result="UNKNOWN",
                evidence="Dimension mismatch between job and candidate embeddings.",
                embedding_model=embedding_model,
                embedding_version=embedding_version,
            )

        # Calculate cosine similarity using pgvector, with python fallback for sqlite tests
        bind = self.session.get_bind()
        if bind and bind.dialect.name == "sqlite":
            dot = sum(a * b for a, b in zip(job_embedding, candidate_embedding, strict=False))
            mag_a = math.sqrt(sum(a * a for a in job_embedding))
            mag_b = math.sqrt(sum(b * b for b in candidate_embedding))
            similarity = dot / (mag_a * mag_b) if mag_a and mag_b else 0.0
        else:
            sql = text("SELECT 1 - (cast(:emb1 as vector) <=> cast(:emb2 as vector))")
            res = self.session.execute(
                sql, {"emb1": str(job_embedding), "emb2": str(candidate_embedding)}
            ).scalar()
            similarity = float(res) if res is not None else 0.0

        from typing import Literal

        status: Literal["MATCH", "PARTIAL_MATCH", "NO_MATCH", "UNKNOWN"]
        if similarity >= self.config.semantic_match_threshold:
            status = "MATCH"
            evidence = "Strong semantic alignment."
        elif similarity >= self.config.partial_match_threshold:
            status = "PARTIAL_MATCH"
            evidence = "Partial semantic alignment."
        else:
            status = "NO_MATCH"
            evidence = "Poor semantic alignment."

        return SemanticMatchResult(
            similarity_score=similarity,
            threshold=self.config.semantic_match_threshold,
            result=status,
            evidence=evidence,
            embedding_model=embedding_model,
            embedding_version=embedding_version,
        )
