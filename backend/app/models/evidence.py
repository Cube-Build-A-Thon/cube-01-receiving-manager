from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(..., min_length=1)
    image_id: str = Field(..., min_length=1)
    check_type: str = Field(..., min_length=1)
    observation: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: str = Field(..., min_length=1)
    bounding_region: dict[str, Any] | None = None

    @field_validator("evidence_id", "image_id", "check_type")
    @classmethod
    def validate_required_fields(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Value cannot be empty")
        return value.strip()
