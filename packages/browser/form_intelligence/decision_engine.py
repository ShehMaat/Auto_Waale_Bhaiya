import uuid
from typing import Any, List, Optional

from packages.db.models.candidate import Profile
from packages.db.models.memory import MemoryFact
from packages.schemas.enums import DecisionType, FieldRequirement, FieldSensitivity, FieldType
from packages.schemas.form import DecisionContext, FieldDecision, FormField


class DecisionEngine:
    """
    Evaluates form fields against candidate memory to determine safe browser actions.
    Enforces Phase 8 security constraints.
    """

    def __init__(self) -> None:
        pass

    def decide(
        self,
        field: FormField,
        profile: Optional[Profile] = None,
        memories: Optional[List[MemoryFact]] = None,
        context: Optional[DecisionContext] = None,
    ) -> FieldDecision:
        if context:
            field = context.field
            profile = context.candidate_profile
            memories = context.memory_facts

        memories = memories or []
        classification = field.classification
        if not classification:
            return self._unknown_decision(field)

        # 1. Submission Blocking (Phase 3C strict constraint)
        label_lower = (field.label or "").lower()
        if (
            "submit application" in label_lower
            or "complete application" in label_lower
            or "send application" in label_lower
            or "finish application" in label_lower
        ):
            return FieldDecision(
                decision_id=str(uuid.uuid4()),
                field_id=field.field_id,
                decision_type=DecisionType.BLOCK,
                reason="Final submission is blocked in Phase 3C",
                confidence=1.0,
                source="POLICY",
                policy_version="phase8-v1",
            )

        # 2. Challenge & Authentication Blocking
        if classification.sensitivity == FieldSensitivity.CHALLENGE:
            return FieldDecision(
                decision_id=str(uuid.uuid4()),
                field_id=field.field_id,
                decision_type=DecisionType.PAUSE,
                reason="Challenge detected. Human intervention required.",
                confidence=1.0,
                source="POLICY",
                requires_user=True,
                sensitivity=FieldSensitivity.CHALLENGE,
                policy_version="phase8-v1",
            )

        if classification.sensitivity == FieldSensitivity.AUTHENTICATION:
            return FieldDecision(
                decision_id=str(uuid.uuid4()),
                field_id=field.field_id,
                decision_type=DecisionType.PAUSE,
                reason="Authentication required. Human intervention required.",
                confidence=1.0,
                source="POLICY",
                requires_user=True,
                sensitivity=FieldSensitivity.AUTHENTICATION,
                policy_version="phase8-v1",
            )

        # 2b. Navigational Buttons
        if field.input_type in ["submit", "button", "a"] or "button" in (field.role or "") or field.role == "link":
            label_lower = (field.label or "").lower()
            if any(word in label_lower for word in ["back", "cancel", "clear", "previous"]):
                return FieldDecision(
                    decision_id=str(uuid.uuid4()),
                    field_id=field.field_id,
                    decision_type=DecisionType.BLOCK,
                    reason="Backward navigation or cancellation is blocked",
                    confidence=1.0,
                    source="POLICY",
                    policy_version="phase8-v1",
                )
            
            return FieldDecision(
                decision_id=str(uuid.uuid4()),
                field_id=field.field_id,
                decision_type=DecisionType.AUTO_FILL,
                reason="Auto-click navigational button",
                confidence=1.0,
                source="POLICY",
                value="click",
                proposed_action={"value": "click", "action_type": "click"},
                policy_version="phase8-v1",
            )

        # 3. Memory Mapping & Auto-Fill
        candidate_val, provenance, memory_id, is_conflict = self._find_candidate_value(
            classification.field_type, profile, memories
        )

        if is_conflict:
            return FieldDecision(
                decision_id=str(uuid.uuid4()),
                field_id=field.field_id,
                decision_type=DecisionType.ASK_USER,
                reason="Conflicting candidate memory facts found",
                confidence=0.0,
                source="MULTIPLE",
                requires_user=True,
                policy_version="phase8-v1",
            )

        if candidate_val is not None:
            if classification.sensitivity == FieldSensitivity.SENSITIVE:
                return FieldDecision(
                    decision_id=str(uuid.uuid4()),
                    field_id=field.field_id,
                    decision_type=DecisionType.ASK_USER,
                    reason="Sensitive field requires explicit confirmation",
                    confidence=1.0,
                    source=provenance,
                    provenance=provenance,
                    value=candidate_val,
                    memory_ids=[memory_id] if memory_id else [],
                    requires_user=True,
                    sensitivity=FieldSensitivity.SENSITIVE,
                    policy_version="phase8-v1",
                )

            # Provenance trust check
            trust_level = self.evaluate_trust(provenance)
            if trust_level == "HIGH":
                return FieldDecision(
                    decision_id=str(uuid.uuid4()),
                    field_id=field.field_id,
                    decision_type=DecisionType.AUTO_FILL,
                    reason="High trust candidate value matched",
                    confidence=1.0,
                    source=provenance,
                    provenance=provenance,
                    trust_level=trust_level,
                    value=candidate_val,
                    memory_ids=[memory_id] if memory_id else [],
                    proposed_action={"value": candidate_val},
                    policy_version="phase8-v1",
                )
            elif trust_level == "MEDIUM":
                return FieldDecision(
                    decision_id=str(uuid.uuid4()),
                    field_id=field.field_id,
                    decision_type=DecisionType.SUGGEST,
                    reason="Medium trust value suggested",
                    confidence=0.7,
                    source=provenance,
                    provenance=provenance,
                    trust_level=trust_level,
                    value=candidate_val,
                    memory_ids=[memory_id] if memory_id else [],
                    proposed_action={"value": candidate_val},
                    policy_version="phase8-v1",
                )
            else:
                return FieldDecision(
                    decision_id=str(uuid.uuid4()),
                    field_id=field.field_id,
                    decision_type=DecisionType.ASK_USER,
                    reason="Low trust provenance (inferred/generated) cannot be auto-filled",
                    confidence=0.0,
                    source=provenance,
                    provenance=provenance,
                    trust_level=trust_level,
                    value=candidate_val,
                    memory_ids=[memory_id] if memory_id else [],
                    requires_user=True,
                    policy_version="phase8-v1",
                )

        # 4. Fallback for unmapped fields
        if classification.field_type == FieldType.CUSTOM_QUESTION:
            return self._evaluate_custom_question(field)

        if classification.field_type in [FieldType.MOTIVATION, FieldType.COVER_LETTER]:
            return FieldDecision(
                decision_id=str(uuid.uuid4()),
                field_id=field.field_id,
                decision_type=DecisionType.GENERATE,
                reason="Generative answer required",
                confidence=0.5,
                source="SYSTEM",
                generated=True,
                requires_confirmation=True,
                policy_version="phase8-v1",
            )


        return FieldDecision(
            decision_id=str(uuid.uuid4()),
            field_id=field.field_id,
            decision_type=DecisionType.ASK_USER,
            reason="No trusted candidate answer exists",
            confidence=0.0,
            source="NONE",
            requires_user=classification.requirement != FieldRequirement.OPTIONAL,
            policy_version="phase8-v1",
        )

    def evaluate_trust(self, provenance: str) -> str:
        if provenance in ["USER_CONFIRMED", "EXPLICIT_PROFILE", "VERIFIED_DOCUMENT"]:
            return "HIGH"
        elif provenance in ["RESUME_EXTRACTED", "MEMORY_DERIVED"]:
            return "MEDIUM"
        return "LOW"

    def _evaluate_custom_question(self, field: FormField) -> FieldDecision:
        label = (field.label or "").lower()

        # Authorization
        if "sponsorship" in label or "authorized" in label or "visa" in label:
            return FieldDecision(
                decision_id=str(uuid.uuid4()),
                field_id=field.field_id,
                decision_type=DecisionType.ASK_USER,  # Force ASK_USER or CONFIRM for auth
                reason="Authorization/Sponsorship question",
                confidence=1.0,
                source="POLICY",
                requires_user=True,
                sensitivity=FieldSensitivity.SENSITIVE,
                policy_version="phase8-v1",
            )

        # Sensitive
        if (
            "salary" in label
            or "compensation" in label
            or "race" in label
            or "veteran" in label
            or "disability" in label
        ):
            return FieldDecision(
                decision_id=str(uuid.uuid4()),
                field_id=field.field_id,
                decision_type=DecisionType.ASK_USER,
                reason="Sensitive question",
                confidence=1.0,
                source="POLICY",
                requires_user=True,
                sensitivity=FieldSensitivity.SENSITIVE,
                policy_version="phase8-v1",
            )

        # Narrative
        if "why do you want" in label or "describe" in label or "tell us about" in label:
            return FieldDecision(
                decision_id=str(uuid.uuid4()),
                field_id=field.field_id,
                decision_type=DecisionType.GENERATE,
                reason="Narrative custom question",
                confidence=0.8,
                source="SYSTEM",
                generated=True,
                requires_confirmation=True,
                policy_version="phase8-v1",
            )

        # Default unknown/ambiguous
        return FieldDecision(
            decision_id=str(uuid.uuid4()),
            field_id=field.field_id,
            decision_type=DecisionType.ASK_USER,
            reason="Unknown ambiguous question",
            confidence=0.0,
            source="SYSTEM",
            requires_user=field.classification.requirement != FieldRequirement.OPTIONAL if field.classification else True,
            policy_version="phase8-v1",
        )

    def _find_candidate_value(
        self, field_type: FieldType, profile: Optional[Profile], memories: List[MemoryFact]
    ) -> tuple[Any, str, Optional[str], bool]:
        """Returns (value, provenance, memory_id, is_conflict)"""
        # Hardcoded profile checks first (EXPLICIT_PROFILE -> HIGH TRUST)
        if profile:
            if field_type == FieldType.FIRST_NAME and profile.full_name:
                return profile.full_name.split()[0], "EXPLICIT_PROFILE", None, False
            if field_type == FieldType.LAST_NAME and profile.full_name:
                parts = profile.full_name.split()
                return parts[-1] if len(parts) > 1 else "", "EXPLICIT_PROFILE", None, False
            if field_type == FieldType.FULL_NAME and profile.full_name:
                return profile.full_name, "EXPLICIT_PROFILE", None, False
            if field_type == FieldType.PHONE and profile.phone:
                return profile.phone, "EXPLICIT_PROFILE", None, False

        # Memory checks
        matching = [m for m in memories if m.category == field_type.value]
        if len(matching) > 1:
            # Check for conflict
            val1 = str(matching[0].value).strip().lower()
            for m in matching[1:]:
                if str(m.value).strip().lower() != val1:
                    return None, "MULTIPLE", None, True

        if matching:
            return matching[0].value, matching[0].provenance, str(matching[0].id), False

        return None, "NONE", None, False

    def _unknown_decision(self, field: FormField) -> FieldDecision:
        return FieldDecision(
            decision_id=str(uuid.uuid4()),
            field_id=field.field_id,
            decision_type=DecisionType.ASK_USER,
            reason="Field classification is unknown",
            confidence=0.0,
            source="NONE",
            requires_user=True,
            policy_version="phase8-v1",
        )
