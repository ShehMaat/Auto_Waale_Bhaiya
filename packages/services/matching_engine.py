import uuid
from typing import List, Literal, Tuple

from sqlalchemy.orm import Session

from packages.config.matching import MatchingConfig
from packages.db.models.jobs import Job, JobMatchScore
from packages.schemas.models import (
    CandidateCanonicalModel,
    JobRequirementSchema,
    MatchExplanation,
    MatchResult,
    MemoryFactSchema,
)
from packages.services.semantic_engine import SemanticSimilarityEngine


class HardConstraintEngine:
    """Dedicated evaluator for strictly required constraints."""

    def evaluate(
        self, candidate: CandidateCanonicalModel, requirements: List[JobRequirementSchema]
    ) -> Tuple[Literal["PASS", "FAIL", "UNKNOWN"], List[str], List[str]]:
        failures = []
        unknowns = []

        trusted_facts = [
            f
            for f in candidate.facts
            if f.status == "CONFIRMED"
            or f.trust_level in ["USER_CONFIRMED", "VERIFIED_DOCUMENT", "EXPLICIT_PROFILE"]
        ]

        for req in requirements:
            if not req.required:
                continue

            status, reason = self._evaluate_single_constraint(req, trusted_facts)
            if status == "FAIL":
                failures.append(f"Failed mandatory requirement: {req.name} - {reason}")
            elif status == "UNKNOWN":
                unknowns.append(req.name)

        if failures:
            return "FAIL", failures, unknowns
        if unknowns:
            return "UNKNOWN", failures, unknowns
        return "PASS", failures, unknowns

    def _evaluate_single_constraint(
        self, req: JobRequirementSchema, facts: List[MemoryFactSchema]
    ) -> Tuple[Literal["PASS", "FAIL", "UNKNOWN"], str]:
        req_cat = req.category
        req_val = req.normalized_name or req.name

        relevant_facts = [f for f in facts if f.category.upper() == req_cat.value]

        if not relevant_facts:
            return "UNKNOWN", "No data available in candidate profile."

        # Simplify logic for tests/evaluation
        match_found = False
        for f in relevant_facts:
            if (
                req_val.lower() in f.value.lower()
                or req_val.lower() in str(f.normalized_value).lower()
            ):
                match_found = True
                break

        if not match_found:
            return "FAIL", "REQUIRED_GAP"
        return "PASS", ""


class FuzzyMatchingEngine:
    """Evaluates preferred requirements."""

    def evaluate(
        self, candidate: CandidateCanonicalModel, requirements: List[JobRequirementSchema]
    ) -> Tuple[float, List[str]]:
        preferred_reqs = [r for r in requirements if r.preferred]
        if not preferred_reqs:
            return 1.0, []

        trusted_facts = [
            f
            for f in candidate.facts
            if f.status == "CONFIRMED"
            or f.trust_level in ["USER_CONFIRMED", "VERIFIED_DOCUMENT", "EXPLICIT_PROFILE"]
        ]

        matches = []
        score = 0.0

        for req in preferred_reqs:
            req_cat = req.category
            req_val = req.normalized_name or req.name
            relevant_facts = [f for f in trusted_facts if f.category.upper() == req_cat.value]

            match_found = any(
                req_val.lower() in f.value.lower()
                or req_val.lower() in str(f.normalized_value).lower()
                for f in relevant_facts
            )
            if match_found:
                score += 1.0
                matches.append(req.name)

        return score / len(preferred_reqs), matches


class MatchingEngine:
    def __init__(self, session: Session, config: MatchingConfig):
        self.session = session
        self.config = config
        self.hard_constraint_engine = HardConstraintEngine()
        self.fuzzy_engine = FuzzyMatchingEngine()
        self.semantic_engine = SemanticSimilarityEngine(session, config)

    def calculate_match_score(
        self,
        candidate: CandidateCanonicalModel,
        job: Job,
        requirements: List[JobRequirementSchema],
        candidate_embedding: List[float],
    ) -> MatchResult:
        """Calculates a multi-layered match score combining deterministic rules and semantic embeddings."""  # noqa: E501

        # 1. Hard constraints
        constraint_status, failures, unknowns = self.hard_constraint_engine.evaluate(
            candidate, requirements
        )

        # 2. Fuzzy matching
        pref_score, pref_matches = self.fuzzy_engine.evaluate(candidate, requirements)

        # 3. Semantic matching
        semantic_res = self.semantic_engine.calculate_similarity(
            job.embedding,
            candidate_embedding,
            job.embedding_model or "unknown",
            job.embedding_version or "unknown",
        )

        semantic_score = semantic_res.similarity_score

        # 4. Feature Scoring
        skill_score = pref_score
        experience_score = 0.90  # Stubbed or from structured extracted fields
        education_score = 1.0  # Stubbed or from structured extracted fields

        overall = (
            (semantic_score * self.config.semantic_weight)
            + (skill_score * self.config.skill_weight)
            + (experience_score * self.config.experience_weight)
            + (education_score * self.config.education_weight)
        )

        if constraint_status == "FAIL":
            overall = 0.0
            explanation_text = (
                f"Candidate failed hard constraints. Semantic match: {semantic_res.result}."
            )
        elif constraint_status == "UNKNOWN":
            explanation_text = f"Candidate matches {overall * 100:.1f}% but missing data leaves some constraints UNKNOWN. Semantic match: {semantic_res.result}."  # noqa: E501
        else:
            explanation_text = f"Candidate matches {overall * 100:.1f}% of the core requirements. Semantic match: {semantic_res.result}."  # noqa: E501

        explanation = MatchExplanation(
            matched_requirements=[
                r.name
                for r in requirements
                if r.required
                and r.name not in unknowns
                and r.name
                not in (
                    f.split(" - ")[0].replace("Failed mandatory requirement: ", "")
                    for f in failures
                )
            ],
            missing_requirements=failures,
            preferred_matches=pref_matches,
            constraint_failures=failures,
            unknowns=unknowns,
            semantic_matches=[semantic_res.evidence]
            if semantic_res.result in ["MATCH", "PARTIAL_MATCH"]
            else [],
            explanation=explanation_text,
        )

        result = MatchResult(
            job_id=job.id,
            overall_score=overall,
            hard_constraint_score=1.0 if constraint_status == "PASS" else 0.0,
            skill_score=skill_score,
            experience_score=experience_score,
            education_score=education_score,
            semantic_score=semantic_score,
            preference_score=pref_score,
            explanation=explanation,
            matching_version="v2",
            scoring_config_version=self.config.config_version,
            embedding_model=semantic_res.embedding_model,
            embedding_version=semantic_res.embedding_version,
            candidate_profile_version="latest",
            job_content_hash=job.content_hash,
        )

        self._persist_score(candidate.profile.id, result)
        return result

    def _persist_score(self, user_id: uuid.UUID, result: MatchResult) -> None:
        score_entry = (
            self.session.query(JobMatchScore)
            .filter(JobMatchScore.job_id == result.job_id, JobMatchScore.user_id == user_id)
            .first()
        )

        if score_entry:
            score_entry.score = result.overall_score
            score_entry.reasoning = result.explanation.explanation
            score_entry.matching_version = result.matching_version
            score_entry.scoring_config_version = result.scoring_config_version
            score_entry.embedding_model = result.embedding_model
            score_entry.embedding_version = result.embedding_version
            score_entry.candidate_profile_version = result.candidate_profile_version
            score_entry.job_content_hash = result.job_content_hash
        else:
            score_entry = JobMatchScore(
                job_id=result.job_id,
                user_id=user_id,
                score=result.overall_score,
                reasoning=result.explanation.explanation,
                matching_version=result.matching_version,
                scoring_config_version=result.scoring_config_version,
                embedding_model=result.embedding_model,
                embedding_version=result.embedding_version,
                candidate_profile_version=result.candidate_profile_version,
                job_content_hash=result.job_content_hash,
            )
            self.session.add(score_entry)
        self.session.commit()
