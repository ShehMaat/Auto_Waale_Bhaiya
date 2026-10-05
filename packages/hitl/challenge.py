import uuid
from typing import Any, Optional

from packages.hitl.manager import HITLManager
from packages.schemas.enums import HITLRequestType
from packages.schemas.hitl import HITLRequestCreate


class ChallengeManager:
    def __init__(self, hitl_manager: HITLManager):
        self.hitl_manager = hitl_manager

    async def detect_and_pause_for_challenge(
        self,
        application_id: uuid.UUID,
        workflow_id: uuid.UUID,
        user_id: uuid.UUID,
        challenge_type: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Creates a HITL request specifically for a challenge, effectively
        ensuring the orchestrator will pause.
        Final submission and auto-bypassing are strictly prohibited.
        """
        req_type = HITLRequestType.AUTHENTICATION
        if challenge_type.upper() == "CAPTCHA":
            req_type = HITLRequestType.CAPTCHA
        elif challenge_type.upper() == "OTP":
            req_type = HITLRequestType.OTP
        elif "2FA" in challenge_type.upper():
            req_type = HITLRequestType.TWO_FACTOR_AUTH

        req = HITLRequestCreate(
            application_id=application_id,
            workflow_id=workflow_id,
            user_id=user_id,
            request_type=req_type,
            title=f"Manual Intervention Required: {challenge_type}",
            description="The agent encountered a challenge it cannot autonomously bypass due to strict security policies. Please intervene in the browser session or provide the required code.",  # noqa: E501
            context_json=context or {},
            required_action="Intervene in the review UI or provide the required code.",
            priority=100,
        )

        self.hitl_manager.create_request(req)
