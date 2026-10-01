from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.core.config import get_settings
from backend.app.core.decision_engine import (
    evaluate_component_check,
    evaluate_damage_check,
    evaluate_overall,
    evaluate_quantity_check,
    evaluate_sku_check,
    evaluate_variant_check,
)
from backend.app.models.evidence import Evidence
from backend.app.models.inspection import InspectionCheck, VisualObservation

VALID_CHECK_TYPES = {"sku", "quantity", "variant", "damage", "components", "carton"}


class VisionObservationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_type: str = Field(..., min_length=1)
    observation: str | int | list[str] | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: str = Field(..., min_length=1)

    @field_validator("check_type")
    @classmethod
    def validate_check_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_CHECK_TYPES:
            raise ValueError(f"Unsupported check type: {value}")
        return normalized


class VisionImageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_id: str = Field(..., min_length=1)
    visibility: str = Field(default="clear")
    observations: list[VisionObservationItem] = Field(default_factory=list)


class VisionAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    images: list[VisionImageResult] = Field(default_factory=list)


class VisionService:
    def __init__(self, inspection):
        self.inspection = inspection

    @staticmethod
    def _make_demo_scenario(scenario_name: str | None) -> VisionAnalysisResponse:
        scenario = (scenario_name or "correct_shipment").strip().lower().replace(" ", "_")
        demos = {
            "correct_shipment": {
                "images": [
                    {
                        "image_id": "demo-1",
                        "visibility": "clear",
                        "observations": [
                            {"check_type": "sku", "observation": "BLUE-BOTTLE-001", "confidence": 0.97, "description": "SKU label matches the PO."},
                            {"check_type": "quantity", "observation": 24, "confidence": 0.93, "description": "24 units are visible and countable."},
                            {"check_type": "variant", "observation": "Blue", "confidence": 0.96, "description": "Packaging colour matches the expected variant."},
                            {"check_type": "damage", "observation": "none", "confidence": 0.95, "description": "No visible carton or product damage."},
                            {"check_type": "components", "observation": ["cap", "label"], "confidence": 0.9, "description": "Required components are present."},
                        ],
                    }
                ]
            },
            "short_shipment": {
                "images": [
                    {
                        "image_id": "demo-1",
                        "visibility": "clear",
                        "observations": [
                            {"check_type": "sku", "observation": "BLUE-BOTTLE-001", "confidence": 0.97, "description": "SKU label matches the PO."},
                            {"check_type": "quantity", "observation": 22, "confidence": 0.92, "description": "22 units are visible; 2 units are missing."},
                            {"check_type": "variant", "observation": "Blue", "confidence": 0.96, "description": "Packaging colour matches the expected variant."},
                            {"check_type": "damage", "observation": "none", "confidence": 0.95, "description": "No visible carton or product damage."},
                        ],
                    }
                ]
            },
            "wrong_variant": {
                "images": [
                    {
                        "image_id": "demo-1",
                        "visibility": "clear",
                        "observations": [
                            {"check_type": "sku", "observation": "BLUE-BOTTLE-001", "confidence": 0.96, "description": "SKU label is visible and matches the product."},
                            {"check_type": "quantity", "observation": 24, "confidence": 0.93, "description": "Quantity matches the expected count."},
                            {"check_type": "variant", "observation": "Red", "confidence": 0.97, "description": "The product is visibly red rather than blue."},
                            {"check_type": "damage", "observation": "none", "confidence": 0.95, "description": "No visible carton or product damage."},
                        ],
                    }
                ]
            },
            "damaged_carton": {
                "images": [
                    {
                        "image_id": "demo-1",
                        "visibility": "clear",
                        "observations": [
                            {"check_type": "sku", "observation": "BLUE-BOTTLE-001", "confidence": 0.96, "description": "SKU label is visible and matches the PO."},
                            {"check_type": "quantity", "observation": 24, "confidence": 0.94, "description": "The full count is visible."},
                            {"check_type": "variant", "observation": "Blue", "confidence": 0.95, "description": "The variant matches the expected Blue shipment."},
                            {"check_type": "damage", "observation": ["crushing"], "confidence": 0.9, "description": "Carton corner shows visible crushing."},
                        ],
                    }
                ]
            },
            "ambiguous": {
                "images": [
                    {
                        "image_id": "demo-1",
                        "visibility": "blurred",
                        "observations": [
                            {"check_type": "sku", "observation": None, "confidence": 0.4, "description": "The labelling is too blurred to read reliably."},
                            {"check_type": "quantity", "observation": None, "confidence": 0.35, "description": "Units are partially occluded and cannot be counted reliably."},
                            {"check_type": "variant", "observation": None, "confidence": 0.3, "description": "Colour cannot be confirmed with confidence."},
                            {"check_type": "damage", "observation": "uncertain", "confidence": 0.42, "description": "The image does not allow a reliable damage assessment."},
                        ],
                    }
                ]
            },
        }

        payload = demos.get(scenario)
        if payload is None:
            payload = demos["correct_shipment"]
        return VisionAnalysisResponse.model_validate(payload)

    def analyze(self, scenario: str | None = None) -> dict[str, Any]:
        settings = get_settings()
        if settings.demo_mode:
            payload = self._make_demo_scenario(scenario)
        else:
            if not settings.api_key:
                raise ValueError("AI analysis is not configured. Set AI_API_KEY or OPENAI_API_KEY in the environment.")
            try:
                import openai
            except ImportError as exc:  # pragma: no cover - handled by env constraints
                raise RuntimeError("The OpenAI Python SDK is not installed. Add openai to backend requirements.") from exc

            client = openai.OpenAI(api_key=settings.api_key, base_url=settings.openai_base_url or None)
            image_payload = []
            for image in self.inspection.images:
                image_path = image.image_path
                with open(image_path, "rb") as handle:
                    image_payload.append({
                        "type": "input_image",
                        "image_url": f"data:{image.mime_type};base64,{__import__('base64').b64encode(handle.read()).decode('utf-8')}",
                    })

            prompt = "Inspect the incoming receiving images and report only visible evidence. Do not guess hidden quantities or infer missing components unless there is clear visible evidence. Distinguish not visible from missing. Report uncertainty instead of guessing. Do not make the final business decision; only provide structured evidence for the receiving manager."
            response = client.responses.create(
                model=settings.ai_model,
                input=[
                    {"role": "user", "content": [{"type": "input_text", "text": prompt}] + image_payload},
                ],
                response_format={"type": "json_schema", "json_schema": {"name": "receiving_analysis", "schema": {"type": "object", "properties": {"images": {"type": "array", "items": {"type": "object", "properties": {"image_id": {"type": "string"}, "visibility": {"type": "string"}, "observations": {"type": "array", "items": {"type": "object", "properties": {"check_type": {"type": "string"}, "observation": {"anyOf": [{"type": "string"}, {"type": "integer"}, {"type": "array", "items": {"type": "string"}}]}, "confidence": {"type": "number"}, "description": {"type": "string"}}, "required": ["check_type", "confidence", "description"], "additionalProperties": False}}}, "required": ["image_id", "observations"], "additionalProperties": False}}}, "required": ["images"], "additionalProperties": False}}},
            )
            try:
                raw_text = response.output_text
                payload = VisionAnalysisResponse.model_validate_json(raw_text)
            except Exception:
                try:
                    payload = VisionAnalysisResponse.model_validate(response.model_dump())
                except Exception as exc:  # pragma: no cover
                    raise ValueError(f"AI returned malformed structured output: {exc}") from exc

        validated = self._validate_payload(payload)
        return self._build_result(validated)

    def _validate_payload(self, payload: VisionAnalysisResponse) -> VisionAnalysisResponse:
        valid_image_ids = {image.image_id for image in self.inspection.images}
        if not self.inspection.images and not payload.images:
            return payload

        for image_result in payload.images:
            if self.inspection.images and image_result.image_id not in valid_image_ids:
                raise ValueError(f"AI response referenced an unknown image_id: {image_result.image_id}")
            if image_result.visibility.strip().lower() not in {"clear", "blurred", "occluded", "dark", "uncertain"}:
                image_result.visibility = "uncertain"
            for observation in image_result.observations:
                if observation.confidence < 0 or observation.confidence > 1:
                    raise ValueError("Observation confidence must be between 0 and 1.")
        return payload

    def _build_result(self, payload: VisionAnalysisResponse) -> dict[str, Any]:
        evidence_list: list[Evidence] = []
        visual_observations: list[VisualObservation] = []

        for image_result in payload.images:
            image_observations = []
            for item in image_result.observations:
                evidence = Evidence(
                    evidence_id=f"EVD-{len(evidence_list) + 1:04d}",
                    image_id=image_result.image_id,
                    check_type=item.check_type,
                    observation=str(item.observation) if item.observation is not None else "not_visible",
                    confidence=float(item.confidence),
                    description=item.description,
                    bounding_region=None,
                )
                evidence_list.append(evidence)
                image_observations.append(item)

            visual_observations.append(
                VisualObservation(
                    detected_sku=self._first_observation_value(image_result.observations, "sku"),
                    detected_product_name=None,
                    observed_quantity=self._first_numeric_observation(image_result.observations, "quantity"),
                    observed_cartons=None,
                    observed_units_per_carton=None,
                    detected_variant=self._first_observation_value(image_result.observations, "variant"),
                    damage_types=[str(v.observation) for v in image_result.observations if v.check_type == "damage" and v.observation not in {None, "none", "no_damage", "uncertain"}],
                    missing_components=[],
                    visibility_quality=image_result.visibility,
                    confidence=max((obs.confidence for obs in image_result.observations), default=0.0),
                )
            )

        checks = self._build_checks(payload)
        decision = evaluate_overall([check.model_dump(mode="json") for check in checks])
        return {
            "decision": decision,
            "checks": [check.model_dump(mode="json") for check in checks],
            "evidence": [item.model_dump(mode="json") for item in evidence_list],
            "observations": [item.model_dump(mode="json") for item in visual_observations],
        }

    def _build_checks(self, payload: VisionAnalysisResponse) -> list[InspectionCheck]:
        observations_by_type: dict[str, Any] = {}
        for image_result in payload.images:
            for item in image_result.observations:
                observations_by_type.setdefault(item.check_type, []).append(item)

        quantity = self._first_numeric_observation(payload.images[0].observations, "quantity") if payload.images else None
        carton = self._first_numeric_observation(payload.images[0].observations, "carton") if payload.images else None
        variant = self._first_observation_value(payload.images[0].observations, "variant") if payload.images else None
        sku = self._first_observation_value(payload.images[0].observations, "sku") if payload.images else None
        observed_cartons = carton if carton is not None else (self.inspection.po.expected_cartons if quantity is not None else None)
        damage = []
        for item in payload.images[0].observations if payload.images else []:
            if item.check_type == "damage" and item.observation not in {None, "none", "no_damage", "uncertain"}:
                damage.append(str(item.observation))
        components = []
        for item in payload.images[0].observations if payload.images else []:
            if item.check_type == "components" and isinstance(item.observation, list):
                components = [str(value) for value in item.observation]
                break

        sku_result = evaluate_sku_check(self.inspection.po.sku, sku)
        quantity_result = evaluate_quantity_check(self.inspection.po.expected_quantity, quantity)
        carton_result = evaluate_quantity_check(self.inspection.po.expected_cartons, observed_cartons)
        variant_result = evaluate_variant_check(self.inspection.po.variant, variant)
        damage_result = evaluate_damage_check(damage)
        component_result = evaluate_component_check(self.inspection.po.expected_components, components)

        checks = [
            InspectionCheck(
                check_name="sku_check",
                status=sku_result["status"],
                expected_value=self.inspection.po.sku,
                observed_value=sku,
                reason=sku_result["reason"],
                confidence=max((obs.confidence for obs in observations_by_type.get("sku", []) if obs.confidence is not None), default=0.0),
            ),
            InspectionCheck(
                check_name="quantity_check",
                status=quantity_result["status"],
                expected_value=self.inspection.po.expected_quantity,
                observed_value=quantity,
                reason=quantity_result["reason"],
                confidence=max((obs.confidence for obs in observations_by_type.get("quantity", []) if obs.confidence is not None), default=0.0),
            ),
            InspectionCheck(
                check_name="carton_check",
                status=carton_result["status"],
                expected_value=self.inspection.po.expected_cartons,
                observed_value=observed_cartons,
                reason=carton_result["reason"],
                confidence=max((obs.confidence for obs in observations_by_type.get("carton", []) if obs.confidence is not None), default=0.0),
            ),
            InspectionCheck(
                check_name="variant_check",
                status=variant_result["status"],
                expected_value=self.inspection.po.variant,
                observed_value=variant,
                reason=variant_result["reason"],
                confidence=max((obs.confidence for obs in observations_by_type.get("variant", []) if obs.confidence is not None), default=0.0),
            ),
            InspectionCheck(
                check_name="damage_check",
                status=damage_result["status"],
                expected_value="none",
                observed_value=damage,
                reason=damage_result["reason"],
                confidence=max((obs.confidence for obs in observations_by_type.get("damage", []) if obs.confidence is not None), default=0.0),
            ),
            InspectionCheck(
                check_name="component_check",
                status=component_result["status"],
                expected_value=self.inspection.po.expected_components,
                observed_value=components,
                reason=component_result["reason"],
                confidence=max((obs.confidence for obs in observations_by_type.get("components", []) if obs.confidence is not None), default=0.0),
            ),
        ]
        return checks

    @staticmethod
    def _first_observation_value(observations: list[VisionObservationItem], check_type: str):
        for item in observations:
            if item.check_type == check_type:
                return item.observation
        return None

    @staticmethod
    def _first_numeric_observation(observations: list[VisionObservationItem], check_type: str):
        for item in observations:
            if item.check_type == check_type and isinstance(item.observation, (int, float)):
                return int(item.observation)
        return None
