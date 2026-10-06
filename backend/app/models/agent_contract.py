from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.inspection import FinalDecision, InspectionCheck, VisualObservation
from backend.app.models.po import PurchaseOrder

AgentErrorCode = Literal[
    "INVALID_REQUEST",
    "INVALID_AGENT",
    "UNSUPPORTED_ACTION",
    "MISSING_PAYLOAD",
    "INVALID_PURCHASE_ORDER",
    "NO_EVIDENCE",
    "ANALYSIS_FAILED",
    "VISION_TIMEOUT",
    "INTERNAL_ERROR",
]


class ReceivingEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(..., min_length=1)
    image_id: str = Field(..., min_length=1)
    check_type: Literal["sku", "quantity", "variant", "damage", "components", "carton"]
    observation: str | int | list[str] | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: str = Field(..., min_length=1)
    bounding_region: dict[str, Any] | None = None

    @field_validator("evidence_id", "image_id", "description")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value cannot be empty")
        return value


class ReceivingPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    purchase_order: PurchaseOrder
    shipment: dict[str, Any]
    evidence: list[ReceivingEvidence]


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    agent: Literal["receiving-manager"]
    action: Literal["verify_receiving"]
    payload: ReceivingPayload
    metadata: dict[str, Any] | None = None

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id cannot be empty")
        return value


class AgentError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: AgentErrorCode
    message: str = Field(..., min_length=1)
    retryable: bool
    details: dict[str, Any] | None = None


class AgentNextAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: Literal["recovery-manager"]
    reason: str = Field(..., min_length=1)
    priority: Literal["low", "medium", "high"]


class ReceivingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    po_id: str = Field(..., min_length=1)
    decision: FinalDecision
    checks: list[InspectionCheck]
    evidence: list[ReceivingEvidence]
    observations: list[VisualObservation]
    findings: list[InspectionCheck]
    next_action: AgentNextAction | None


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    agent: Literal["receiving-manager"] = "receiving-manager"
    status: Literal["success", "failed", "partial"]
    result: ReceivingResult | None = None
    error: AgentError | None = None
    metadata: dict[str, Any] | None = None


class AgentCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: Literal["receiving-manager"] = "receiving-manager"
    version: Literal["1.0.0"] = "1.0.0"
    protocol_version: Literal["1.0"] = "1.0"
    capabilities: list[
        Literal[
            "shipment_verification",
            "sku_verification",
            "quantity_verification",
            "carton_verification",
            "variant_verification",
            "damage_detection",
            "component_verification",
        ]
    ]
    actions: list[Literal["verify_receiving"]]


class AgentHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    agent: Literal["receiving-manager"] = "receiving-manager"
    version: Literal["1.0.0"] = "1.0.0"
