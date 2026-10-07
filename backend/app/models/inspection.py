from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .evidence import Evidence
from .po import PurchaseOrder

InspectionStatus = Literal["draft", "pending", "completed", "PENDING_REVIEW"]
DecisionStatus = Literal["PASS", "FAIL", "UNCERTAIN", "NOT_REQUIRED"]
FinalDecision = Literal["PASS", "EXCEPTION", "UNCERTAIN"]


class ReceivingImage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_id: str = Field(..., min_length=1)
    inspection_id: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    stored_filename: str = Field(..., min_length=1)
    image_path: str = Field(..., min_length=1)
    image_type: str = Field(default="receiving_photo")
    mime_type: str = Field(default="image/jpeg")
    file_size: int = Field(default=0, ge=0)
    processing_state: Literal["uploaded", "ready", "analyzing", "analyzed", "failed"] = "uploaded"
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("image_id", "inspection_id", "filename", "stored_filename", "image_path")
    @classmethod
    def validate_required_fields(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Value cannot be empty")
        return value.strip()


class VisualObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detected_sku: str | None = None
    detected_product_name: str | None = None
    observed_quantity: int | None = Field(default=None, ge=0)
    observed_cartons: int | None = Field(default=None, ge=0)
    observed_units_per_carton: int | None = Field(default=None, ge=1)
    detected_variant: str | None = None
    damage_types: list[str] = Field(default_factory=list)
    missing_components: list[str] = Field(default_factory=list)
    visibility_quality: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("detected_sku", "detected_product_name", "detected_variant", "visibility_quality")
    @classmethod
    def trim_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class InspectionCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_name: str = Field(..., min_length=1)
    status: DecisionStatus
    expected_value: str | int | list[str] | None = None
    observed_value: str | int | list[str] | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("check_name")
    @classmethod
    def validate_check_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("check_name cannot be empty")
        return value.strip()


class EvidenceSubject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    po_number: str
    po_line: str | None = None
    sku: str
    asin: str | None = None


class EvidenceImageDigest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    view: str
    sha256_digest: str = Field(..., min_length=64, max_length=64)


class SealedInspectionCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_key: str
    verdict: DecisionStatus
    observed_state: str | int | list[str] | None = None
    reason_code: str
    measurements: dict[str, str | int | list[str] | None] = Field(default_factory=dict)
    model_version: str
    rule_ids: list[str] = Field(default_factory=list)


class EvidenceOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: FinalDecision
    disposition: Literal["ACCEPT", "EXCEPTION", "HOLD"]
    prep_hold: bool


class InspectionOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator_id: str
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    before_verdict: FinalDecision
    after_verdict: FinalDecision
    before_content_hash: str
    after_content_hash: str


class SealedEvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    schema_version: str
    organization_id: str
    subject: EvidenceSubject
    images: list[EvidenceImageDigest] = Field(default_factory=list)
    checks: list[SealedInspectionCheck] = Field(default_factory=list)
    outcome: EvidenceOutcome
    overrides: list[InspectionOverride] = Field(default_factory=list)
    status: InspectionStatus
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_hash: str = Field(..., min_length=64, max_length=64)


class Inspection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inspection_id: str = Field(..., min_length=1)
    po: PurchaseOrder
    images: list[ReceivingImage] = Field(default_factory=list)
    observations: list[VisualObservation] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    checks: list[InspectionCheck] = Field(default_factory=list)
    organization_id: str = "default"
    analysis_records: list[SealedEvidenceRecord] = Field(default_factory=list)
    overrides: list[InspectionOverride] = Field(default_factory=list)
    prep_hold: bool = False
    final_decision: FinalDecision = "UNCERTAIN"
    override_decision: FinalDecision | None = None
    override_reason: str | None = None
    analysis_failure_reason_code: str | None = None
    agent_summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: InspectionStatus = "draft"

    @field_validator("inspection_id")
    @classmethod
    def validate_inspection_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("inspection_id cannot be empty")
        return value.strip()


class InspectionResult(BaseModel):
    inspection_id: str = Field(..., min_length=1)
    po_id: str = Field(..., min_length=1)
    checks: list[InspectionCheck] = Field(default_factory=list)
    overall_decision: FinalDecision
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
