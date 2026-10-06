from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.core.config import get_settings
from backend.app.core.decision_engine import (
    evaluate_component_check,
    evaluate_carton_check,
    evaluate_damage_check,
    evaluate_overall,
    evaluate_quantity_check,
    evaluate_sku_check,
    evaluate_variant_check,
)
from backend.app.models.evidence import Evidence
from backend.app.models.inspection import InspectionCheck, VisualObservation

VALID_CHECK_TYPES = {"sku", "quantity", "variant", "damage", "components", "carton", "units_per_carton"}
VISION_ANALYSIS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "images": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "image_id": {"type": "string"},
                    "visibility": {
                        "type": "string",
                        "enum": ["clear", "blurred", "occluded", "dark", "uncertain"],
                    },
                    "observations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "check_type": {
                                    "type": "string",
                                    "enum": sorted(VALID_CHECK_TYPES),
                                },
                                "observation": {
                                    "anyOf": [
                                        {"type": "string"},
                                        {"type": "integer"},
                                        {"type": "array", "items": {"type": "string"}},
                                        {"type": "null"},
                                    ]
                                },
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "description": {"type": "string"},
                            },
                            "required": ["check_type", "observation", "confidence", "description"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["image_id", "visibility", "observations"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["images"],
    "additionalProperties": False,
}


class VisionObservationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_type: str = Field(..., min_length=1)
    observation: str | int | list[str] | None
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
    visibility: Literal["clear", "blurred", "occluded", "dark", "uncertain"]
    observations: list[VisionObservationItem]


class VisionAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    images: list[VisionImageResult]


class VisionService:
    def __init__(self, inspection):
        self.inspection = inspection

    @staticmethod
    def _make_demo_scenario(scenario_name: str | None, inspection: Any | None = None) -> VisionAnalysisResponse:
        scenario = (scenario_name or "correct_shipment").strip().lower().replace(" ", "_")
        image_id = inspection.images[0].image_id if inspection and inspection.images else "demo-1"
        demos = {
            "correct_shipment": {
                "images": [
                    {
                        "image_id": image_id,
                        "visibility": "clear",
                        "observations": [
                            {"check_type": "sku", "observation": "BLUE-BOTTLE-001", "confidence": 0.97, "description": "SKU label matches the PO."},
                            {"check_type": "quantity", "observation": 24, "confidence": 0.93, "description": "24 units are visible and countable."},
                            {"check_type": "carton", "observation": 2, "confidence": 0.93, "description": "Two cartons are visible."},
                            {"check_type": "units_per_carton", "observation": 12, "confidence": 0.93, "description": "Twelve units per carton are visible."},
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
                        "image_id": image_id,
                        "visibility": "clear",
                        "observations": [
                            {"check_type": "sku", "observation": "BLUE-BOTTLE-001", "confidence": 0.97, "description": "SKU label matches the PO."},
                            {"check_type": "quantity", "observation": 22, "confidence": 0.92, "description": "22 units are visible; 2 units are missing."},
                            {"check_type": "carton", "observation": 2, "confidence": 0.93, "description": "Two cartons are visible."},
                            {"check_type": "units_per_carton", "observation": 12, "confidence": 0.93, "description": "Twelve units per carton are visible."},
                            {"check_type": "variant", "observation": "Blue", "confidence": 0.96, "description": "Packaging colour matches the expected variant."},
                            {"check_type": "damage", "observation": "none", "confidence": 0.95, "description": "No visible carton or product damage."},
                        ],
                    }
                ]
            },
            "wrong_variant": {
                "images": [
                    {
                        "image_id": image_id,
                        "visibility": "clear",
                        "observations": [
                            {"check_type": "sku", "observation": "BLUE-BOTTLE-001", "confidence": 0.96, "description": "SKU label is visible and matches the product."},
                            {"check_type": "quantity", "observation": 24, "confidence": 0.93, "description": "Quantity matches the expected count."},
                            {"check_type": "carton", "observation": 2, "confidence": 0.93, "description": "Two cartons are visible."},
                            {"check_type": "units_per_carton", "observation": 12, "confidence": 0.93, "description": "Twelve units per carton are visible."},
                            {"check_type": "variant", "observation": "Red", "confidence": 0.97, "description": "The product is visibly red rather than blue."},
                            {"check_type": "damage", "observation": "none", "confidence": 0.95, "description": "No visible carton or product damage."},
                        ],
                    }
                ]
            },
            "damaged_carton": {
                "images": [
                    {
                        "image_id": image_id,
                        "visibility": "clear",
                        "observations": [
                            {"check_type": "sku", "observation": "BLUE-BOTTLE-001", "confidence": 0.96, "description": "SKU label is visible and matches the PO."},
                            {"check_type": "quantity", "observation": 24, "confidence": 0.94, "description": "The full count is visible."},
                            {"check_type": "carton", "observation": 2, "confidence": 0.93, "description": "Two cartons are visible."},
                            {"check_type": "units_per_carton", "observation": 12, "confidence": 0.93, "description": "Twelve units per carton are visible."},
                            {"check_type": "variant", "observation": "Blue", "confidence": 0.95, "description": "The variant matches the expected Blue shipment."},
                            {"check_type": "damage", "observation": ["crushing"], "confidence": 0.9, "description": "Carton corner shows visible crushing."},
                        ],
                    }
                ]
            },
            "ambiguous": {
                "images": [
                    {
                        "image_id": image_id,
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
        if inspection:
            if inspection.images:
                template = payload["images"][0]
                payload["images"] = [
                    {**template, "image_id": image.image_id}
                    for image in inspection.images
                ]
            else:
                payload["images"] = []
        return VisionAnalysisResponse.model_validate(payload)

    def analyze(self, scenario: str | None = None) -> dict[str, Any]:
        settings = get_settings()
        if settings.demo_mode:
            payload = self._make_demo_scenario(scenario, self.inspection)
        else:
            if not settings.api_key:
                raise ValueError("AI analysis is not configured. Set AI_API_KEY or OPENAI_API_KEY in the environment.")
            try:
                import openai
            except ImportError as exc:  # pragma: no cover - handled by env constraints
                raise RuntimeError("The OpenAI Python SDK is not installed. Add openai to backend requirements.") from exc

            client = openai.OpenAI(
                api_key=settings.api_key,
                base_url=settings.openai_base_url or None,
                timeout=12.0,
                max_retries=0,
            )
            image_payload = []
            for image in self.inspection.images:
                image_path = image.image_path
                with open(image_path, "rb") as handle:
                    image_payload.append({
                        "type": "input_image",
                        "image_url": f"data:{image.mime_type};base64,{__import__('base64').b64encode(handle.read()).decode('utf-8')}",
                    })

            image_references = "\n".join(
                f"Input image {index} has server image_id {image.image_id}."
                for index, image in enumerate(self.inspection.images, start=1)
            )
            prompt = (
                "Inspect every incoming receiving image and report only visible evidence. "
                "Do not guess hidden quantities or infer missing components unless there is clear visible evidence. "
                "Distinguish not visible from missing and report uncertainty instead of guessing. "
                "Do not make the final business decision; only provide structured evidence for the receiving manager. "
                "Return exactly one images entry for each listed server image_id, and use each ID exactly once. "
                "For each image, report only what is visible in that image. "
                "Do not infer or echo purchase-order expectations; no expected values are provided.\n"
                f"{image_references}"
            )
            response = client.responses.create(
                model=settings.ai_model,
                input=[
                    {"role": "user", "content": [{"type": "input_text", "text": prompt}] + image_payload},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "receiving_analysis",
                        "strict": True,
                        "schema": VISION_ANALYSIS_JSON_SCHEMA,
                    }
                },
            )
            try:
                payload = VisionAnalysisResponse.model_validate_json(response.output_text)
            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError(f"AI returned malformed structured output: {exc}") from exc

        validated = self._validate_payload(payload, require_all_images=not settings.demo_mode)
        return self._build_result(validated)

        validated = self._validate_payload(payload)
        return self._build_result(validated)

    def _validate_payload(
        self, payload: VisionAnalysisResponse, require_all_images: bool = False
    ) -> VisionAnalysisResponse:
        valid_image_ids = {image.image_id for image in self.inspection.images}
        if not self.inspection.images and not payload.images:
            return payload
        if require_all_images and not valid_image_ids:
            raise ValueError("AI response cannot reference images because none were uploaded.")

        for image_result in payload.images:
            if self.inspection.images and image_result.image_id not in valid_image_ids:
                raise ValueError(f"AI response referenced an unknown image_id: {image_result.image_id}")
            if image_result.visibility not in {"clear", "blurred", "occluded", "dark", "uncertain"}:
                raise ValueError("AI response contained an unsupported visibility value.")
            for observation in image_result.observations:
                if observation.confidence < 0 or observation.confidence > 1:
                    raise ValueError("Observation confidence must be between 0 and 1.")
        if require_all_images:
            response_image_ids = [image.image_id for image in payload.images]
            if len(response_image_ids) != len(set(response_image_ids)):
                raise ValueError("AI response must reference each uploaded image exactly once.")
            if set(response_image_ids) != valid_image_ids:
                raise ValueError("AI response must reference every uploaded image exactly once.")
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

        all_observations = [item for image_result in payload.images for item in image_result.observations]
        quantity, quantity_conflict = self._merge_scalar_observations(observations_by_type.get("quantity", []), numeric=True)
        observed_cartons, carton_conflict = self._merge_scalar_observations(observations_by_type.get("carton", []), numeric=True)
        observed_units_per_carton, units_per_carton_conflict = self._merge_scalar_observations(
            observations_by_type.get("units_per_carton", []), numeric=True
        )
        sku, sku_conflict = self._merge_scalar_observations(observations_by_type.get("sku", []))
        variant, variant_conflict = self._merge_scalar_observations(observations_by_type.get("variant", []))
        damage, damage_conflict = self._merge_damage_observations(observations_by_type.get("damage", []))
        components: list[str] = []
        seen_components: set[str] = set()
        for item in all_observations:
            if item.check_type == "components" and isinstance(item.observation, list):
                for value in item.observation:
                    normalized = str(value).strip()
                    if normalized and normalized.lower() not in seen_components:
                        components.append(normalized)
                        seen_components.add(normalized.lower())

        sku_result = evaluate_sku_check(self.inspection.po.sku, sku)
        quantity_result = evaluate_quantity_check(self.inspection.po.expected_quantity, quantity)
        carton_result = evaluate_carton_check(self.inspection.po.expected_cartons, observed_cartons)
        units_per_carton_result = evaluate_quantity_check(self.inspection.po.units_per_carton, observed_units_per_carton)
        variant_result = evaluate_variant_check(self.inspection.po.variant, variant)
        damage_result = evaluate_damage_check(damage)
        component_result = evaluate_component_check(self.inspection.po.expected_components, components)
        for result, conflict, name in (
            (sku_result, sku_conflict, "SKU"),
            (quantity_result, quantity_conflict, "quantity"),
            (carton_result, carton_conflict, "carton count"),
            (units_per_carton_result, units_per_carton_conflict, "units per carton"),
            (variant_result, variant_conflict, "variant"),
            (damage_result, damage_conflict, "damage"),
        ):
            if conflict:
                result.update(status="UNCERTAIN", reason=f"Photos disagree about the observed {name}.")

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
                check_name="units_per_carton_check",
                status=units_per_carton_result["status"],
                expected_value=self.inspection.po.units_per_carton,
                observed_value=observed_units_per_carton,
                reason=units_per_carton_result["reason"],
                confidence=max((obs.confidence for obs in observations_by_type.get("units_per_carton", []) if obs.confidence is not None), default=0.0),
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
    def _numeric_value(value: str | int | list[str] | None) -> int | None:
        if isinstance(value, bool) or isinstance(value, list) or value is None:
            return None
        if isinstance(value, int):
            return value
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in {"unknown", "n/a", "uncertain", "not_available"}:
            return None
        try:
            return int(float(cleaned))
        except ValueError:
            return None

    @classmethod
    def _merge_scalar_observations(
        cls, observations: list[VisionObservationItem], numeric: bool = False
    ) -> tuple[str | int | None, bool]:
        available: list[tuple[str | int, str | int]] = []
        for item in observations:
            value = cls._numeric_value(item.observation) if numeric else item.observation
            if not numeric and isinstance(value, str):
                value = value.strip()
                if not value or value.lower() in {"unknown", "n/a", "uncertain", "not_available"}:
                    value = None
            if value is not None and not isinstance(value, list):
                normalized = str(value).strip().lower() if isinstance(value, str) else value
                available.append((normalized, value))
        if not available:
            return None, False
        if len({normalized for normalized, _ in available}) > 1:
            return None, True
        return available[0][1], False

    @staticmethod
    def _merge_damage_observations(
        observations: list[VisionObservationItem],
    ) -> tuple[list[str] | None, bool]:
        readings: list[list[str]] = []
        for item in observations:
            value = item.observation
            if value is None:
                continue
            values = value if isinstance(value, list) else [value]
            normalized = sorted(str(entry).strip().lower() for entry in values if str(entry).strip())
            if not normalized:
                continue
            readings.append(normalized)
        if not readings:
            return None, False
        signatures = {tuple(reading) for reading in readings}
        if len(signatures) > 1:
            return None, True
        return readings[0], False

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
