from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.app.models.agent_contract import (
    AgentErrorCode,
    AgentRequest,
    ReceivingEvidence,
)
from backend.app.models.inspection import Inspection
from backend.app.services.vision import (
    VisionAnalysisResponse,
    VisionImageResult,
    VisionObservationItem,
    VisionService,
)


class AgentProcessingError(Exception):
    def __init__(
        self,
        code: AgentErrorCode,
        message: str,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details


class ReceivingAgentService:
    def process(self, request: AgentRequest) -> dict[str, Any]:
        evidence = request.payload.evidence
        if not evidence:
            raise AgentProcessingError(
                "NO_EVIDENCE",
                "At least one evidence item is required to verify a shipment.",
            )

        inspection = Inspection(
            inspection_id=request.request_id,
            po=request.payload.purchase_order,
        )
        vision = VisionService(inspection)
        analysis = vision.analyze_observations(self._to_analysis_payload(evidence))

        checks = analysis["checks"]
        failed_checks = [check for check in checks if check["status"] == "FAIL"]
        findings = [check for check in checks if check["status"] != "PASS"]
        next_action = None
        if analysis["decision"] == "EXCEPTION":
            reason = failed_checks[0]["reason"] if failed_checks else "A material receiving exception was detected."
            next_action = {
                "agent": "recovery-manager",
                "reason": reason,
                "priority": "high",
            }

        return {
            "po_id": request.payload.purchase_order.po_id,
            "decision": analysis["decision"],
            "checks": checks,
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "observations": analysis["observations"],
            "findings": findings,
            "next_action": next_action,
        }

    @staticmethod
    def _to_analysis_payload(evidence: list[ReceivingEvidence]) -> VisionAnalysisResponse:
        observations_by_image: dict[str, list[VisionObservationItem]] = defaultdict(list)
        for item in evidence:
            observations_by_image[item.image_id].append(
                VisionObservationItem(
                    check_type=item.check_type,
                    observation=item.observation,
                    confidence=item.confidence,
                    description=item.description,
                )
            )
        return VisionAnalysisResponse(
            images=[
                VisionImageResult(
                    image_id=image_id,
                    visibility="uncertain",
                    observations=observations,
                )
                for image_id, observations in observations_by_image.items()
            ]
        )
