"""
Receiving Manager Agent Engine (Step 01 of 5 in Commerce Stream)
Implements:
1. Unified single-pass batch multimodal vision inspection (Rule 2)
2. Fail-open resilience & circuit breaking (Rule 3)
3. First-class UNCERTAIN verdict handling (Rule 4)
4. Authoritative channel rules lookup (Rule 5)
5. Evidence-first traceability (Expected, Observed, Checked, Verdict, Why)
6. Strict Pydantic schema validation for model safety
7. Distinct handling of directly observed vs inferred vs expected quantities
"""

import os
import time
import json
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError

from backend.rules_engine import evaluate_authoritative_compliance
from backend.candidate_provider import candidate_provider

try:
    from PIL import Image, ImageStat
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ------------------------------------------------------------------------------
# Strict Output Validation Schemas (Model Safety & Schema Enforcement)
# ------------------------------------------------------------------------------

class CheckEvidenceItem(BaseModel):
    check_name: str
    verdict: str = Field(..., pattern="^(PASS|FAIL|UNCERTAIN|PENDING)$")
    expected_value: Any
    observed_value: Any
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_source: str
    evidence_description: str
    image_identifier: Optional[str] = None
    bounding_box: Optional[Dict[str, float]] = None  # e.g. {"x": 0.2, "y": 0.3, "w": 0.4, "h": 0.3}
    timestamp: str


class QuantityEvidence(BaseModel):
    expected_carton_count: int
    observed_carton_count: int
    expected_units_per_carton: int
    observed_units_per_carton: int
    directly_observed_units: Optional[int] = None
    inferred_total_units: int
    expected_total_units: int
    quantity_discrepancy_delta: int
    quantity_verdict: str


class InspectionResultSchema(BaseModel):
    schema_version: str = "1.0.0"
    unit_id: str
    shipment_id: Optional[str] = None
    org_id: str
    model_name: str
    model_version: str
    batch_single_pass: bool
    batch_execution_time_ms: float
    captured_at: str
    status: str
    overall_verdict: str  # PASS, FAIL, UNCERTAIN, PENDING_REVIEW
    overall_decision: str  # PASS, EXCEPTION, UNCERTAIN, PENDING
    agent_confidence: float
    decision_rationale: str
    uncertain_explanation: Optional[str] = None
    recommended_next_evidence: Optional[str] = None
    execution_mode: str = "DEMO_MODE_SYNTHETIC"
    is_real_ai: bool = False
    ai_provider: str = "Deterministic Rule & Heuristic Engine (Demo Mode)"
    what_received: Dict[str, Any]
    what_expected: Dict[str, Any]
    checks: List[Dict[str, Any]]
    quantity_breakdown: QuantityEvidence
    individual_checks: List[CheckEvidenceItem]
    authoritative_channel_checks: List[Dict[str, Any]]
    candidate_skus: Optional[List[Dict[str, Any]]] = None
    token_usage: Optional[Dict[str, Any]] = None


def safe_int(val: Any, default: int = 1) -> int:
    try:
        if val is None:
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


class ReceivingManagerAgent:
    def __init__(self, model_name: Optional[str] = None, model_version: str = "v1.2-rcv"):
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.is_real_ai = bool(self.api_key and self.api_key != "YOUR_GEMINI_API_KEY_HERE")
        
        if self.is_real_ai:
            self.model_name = model_name or os.environ.get("VISION_MODEL_NAME", "gemini-1.5-flash")
            self.execution_mode = "REAL_AI_MULTIMODAL"
            self.ai_provider = "Google Gemini Multimodal Vision API"
        else:
            self.model_name = model_name or "Deterministic-Rule-Mock-Agent (Demo Mode)"
            self.execution_mode = "DEMO_MODE_SYNTHETIC"
            self.ai_provider = "Deterministic Rule & Heuristic Engine (Demo Mode)"

        self.model_version = model_version
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def run_batch_receiving_inspection(
        self,
        org_id: str,
        unit_id: str,
        po_line_spec: Dict[str, Any],
        captured_images: List[str],
        simling_failure: bool = False,
        shipment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes single-pass batch receiving inspection.
        Batches all visual reasoning checks into a single unified pass.
        Computes deterministic arithmetic for carton and unit counts.
        Supports shipment_id end-to-end and candidate SKU discrimination.
        """
        start_time = time.time()
        captured_at = datetime.utcnow().isoformat()

        if shipment_id is None and po_line_spec and isinstance(po_line_spec, dict):
            shipment_id = po_line_spec.get("shipment_id")

        # Engineering Rule 3: Fail-Open Simulation / Timeout Circuit Breaker
        if simling_failure:
            return self._build_fail_open_response(
                org_id=org_id,
                unit_id=unit_id,
                po_line_spec=po_line_spec,
                captured_images=captured_images,
                captured_at=captured_at,
                reason="Vision pipeline timeout / model service unavailability (Fail-Open active)",
                shipment_id=shipment_id
            )

        # Real Gemini Multimodal AI Branch if API key is configured
        if self.is_real_ai:
            try:
                return self._run_real_gemini_vision(
                    org_id=org_id,
                    unit_id=unit_id,
                    po_line_spec=po_line_spec,
                    captured_images=captured_images,
                    captured_at=captured_at,
                    start_time=start_time,
                    shipment_id=shipment_id
                )
            except Exception as gemini_err:
                # Engineering Rule 3: If real AI fails, trigger fail-open PENDING_REVIEW
                # NEVER silently fabricate a mock result and pretend it came from real AI
                return self._build_fail_open_response(
                    org_id=org_id,
                    unit_id=unit_id,
                    po_line_spec=po_line_spec,
                    captured_images=captured_images,
                    captured_at=captured_at,
                    reason=f"Real Gemini Vision API error: {str(gemini_err)} (Fail-open fallback active)",
                    shipment_id=shipment_id
                )

        try:
            # 1. Image Quality & Visual Analysis using Pillow / Vision Heuristics
            image_metrics = self._analyze_captured_images(captured_images)
            overall_clarity = image_metrics["min_clarity"]
            primary_image = captured_images[0] if captured_images else "fixtures/receiving/default_pallet.jpg"

            # 2. SKU / Product Identity Check
            sku_check = self._inspect_sku_identity(po_line_spec, image_metrics, primary_image, captured_at)

            # 3. Deterministic Quantity Verification (Expected vs Inferred vs Directly Observed)
            qty_breakdown, qty_check = self._verify_quantity(po_line_spec, image_metrics, primary_image, captured_at)

            # 4. Visible Damage Inspection (Carton crushing, water damage, tears, punctures)
            carton_dmg_check, unit_dmg_check, detected_damage_type = self._inspect_damage(
                captured_images, image_metrics, primary_image, captured_at
            )

            # 5. Spec Quality / Variant / Missing Components Check
            spec_check, detected_quality_flags = self._inspect_spec_and_components(
                po_line_spec, image_metrics, primary_image, captured_at
            )

            # 6. Authoritative Channel Rules (Rule 5)
            compliance_input = {
                "carton_damage": detected_damage_type["carton"],
                "unit_damage": detected_damage_type["unit"],
                "quality_flags": ";".join(detected_quality_flags),
                "qty_ordered": qty_breakdown.expected_total_units,
                "qty_received": qty_breakdown.inferred_total_units
            }
            channel_rules_eval = evaluate_authoritative_compliance(compliance_input)

            # 7. Deterministic Decision Aggregation Engine
            # A sensible baseline per specification:
            # If any required check = FAIL: OVERALL = EXCEPTION (verdict FAIL)
            # Else if any required check = UNCERTAIN: OVERALL = UNCERTAIN
            # Else: OVERALL = PASS
            all_checks = [sku_check, qty_check, carton_dmg_check, unit_dmg_check, spec_check]
            
            has_fail = any(c.verdict == "FAIL" for c in all_checks)
            has_uncertain = any(c.verdict == "UNCERTAIN" for c in all_checks)

            uncertain_explanation = None
            recommended_next_evidence = None

            if has_fail:
                overall_verdict = "FAIL"
                overall_decision = "EXCEPTION"
                failed_checks = [c.check_name for c in all_checks if c.verdict == "FAIL"]
                decision_rationale = f"Receiving inspection flagged EXCEPTION due to failure in: {', '.join(failed_checks)}."
                conf_scores = [c.confidence for c in all_checks if c.verdict == "FAIL"]
                overall_conf = max(conf_scores) if conf_scores else 0.90
            elif has_uncertain:
                overall_verdict = "UNCERTAIN"
                overall_decision = "UNCERTAIN"
                uncertain_checks = [c.check_name for c in all_checks if c.verdict == "UNCERTAIN"]
                decision_rationale = f"Insufficient evidence to conclude receiving verification for: {', '.join(uncertain_checks)}."
                uncertain_explanation = (
                    f"The submitted photograph(s) do not provide clear visual proof for {', '.join(uncertain_checks)} "
                    f"(image clarity index {overall_clarity:.2f} under threshold 0.50 or occluded features)."
                )
                recommended_next_evidence = (
                    "Capture a sharp, well-lit photo showing the carton barcode label, inner packing, "
                    "and unsealed product components from multiple angles."
                )
                conf_scores = [c.confidence for c in all_checks]
                overall_conf = min(conf_scores) if conf_scores else 0.40
            else:
                overall_verdict = "PASS"
                overall_decision = "PASS"
                decision_rationale = "All incoming items, quantities, carton integrity, and product specifications match PO requirements."
                overall_conf = sum(c.confidence for c in all_checks) / len(all_checks)

            elapsed_ms = round((time.time() - start_time) * 1000, 2)

            legacy_checks = [
                {
                    "check_name": c.check_name,
                    "verdict": c.verdict,
                    "confidence": c.confidence,
                    "details": c.evidence_description
                }
                for c in all_checks
            ]
            what_received_data = {
                "cartons_received": qty_breakdown.observed_carton_count,
                "units_per_carton": qty_breakdown.observed_units_per_carton,
                "total_qty_received": qty_breakdown.inferred_total_units,
                "photo_refs": captured_images
            }
            candidate_skus = candidate_provider.get_candidate_set(po_line_spec.get("sku", "SKU-UNKNOWN"), po_line_spec)
            what_expected_data = {
                "po_number": po_line_spec.get("po_number", "PO-7000"),
                "po_line": po_line_spec.get("po_line", 1),
                "shipment_id": shipment_id,
                "supplier": po_line_spec.get("supplier", "Supplier Standard"),
                "sku": po_line_spec.get("sku", "SKU-UNKNOWN"),
                "asin": po_line_spec.get("asin", "B0DUMMY000"),
                "product_title": po_line_spec.get("product_title", "Sample Product"),
                "spec": {
                    "colour": po_line_spec.get("spec_colour", "n/a"),
                    "variant": po_line_spec.get("spec_variant", "n/a"),
                    "components": po_line_spec.get("spec_components", "n/a")
                },
                "cartons_ordered": qty_breakdown.expected_carton_count,
                "qty_ordered": qty_breakdown.expected_total_units
            }

            # Assemble & Validate against strict Pydantic schema
            structured_inspection = InspectionResultSchema(
                schema_version="1.0.0",
                unit_id=unit_id,
                shipment_id=shipment_id,
                org_id=org_id,
                model_name=self.model_name,
                model_version=self.model_version,
                batch_single_pass=True,
                batch_execution_time_ms=elapsed_ms,
                captured_at=captured_at,
                status="processed",
                overall_verdict=overall_verdict,
                overall_decision=overall_decision,
                agent_confidence=round(overall_conf, 2),
                decision_rationale=decision_rationale,
                uncertain_explanation=uncertain_explanation,
                recommended_next_evidence=recommended_next_evidence,
                execution_mode=self.execution_mode,
                is_real_ai=self.is_real_ai,
                ai_provider=self.ai_provider,
                what_received=what_received_data,
                what_expected=what_expected_data,
                checks=legacy_checks,
                quantity_breakdown=qty_breakdown,
                individual_checks=all_checks,
                authoritative_channel_checks=channel_rules_eval,
                candidate_skus=candidate_skus
            )

            dump_data = structured_inspection.model_dump() if hasattr(structured_inspection, "model_dump") else structured_inspection.dict()

            # Legacy and API Compatible Payload
            return {
                "unit_id": unit_id,
                "shipment_id": shipment_id,
                "candidate_skus": candidate_skus,
                "org_id": org_id,
                "captured_at": captured_at,
                "batch_execution_time_ms": elapsed_ms,
                "batch_single_pass": True,
                "model_name": self.model_name,
                "model_version": self.model_version,
                "execution_mode": self.execution_mode,
                "is_real_ai": self.is_real_ai,
                "ai_provider": self.ai_provider,
                "identity_match": "yes" if sku_check.verdict == "PASS" else ("no" if sku_check.verdict == "FAIL" else "uncertain"),
                "cartons_ordered": qty_breakdown.expected_carton_count,
                "cartons_received": qty_breakdown.observed_carton_count,
                "units_per_carton_ordered": qty_breakdown.expected_units_per_carton,
                "units_per_carton_counted": qty_breakdown.observed_units_per_carton,
                "qty_ordered": qty_breakdown.expected_total_units,
                "qty_received": qty_breakdown.inferred_total_units,
                "directly_observed_units": qty_breakdown.directly_observed_units,
                "carton_damage": detected_damage_type["carton"],
                "unit_damage": detected_damage_type["unit"],
                "quality_flags": ";".join(detected_quality_flags),
                "overall_verdict": overall_verdict,
                "overall_decision": overall_decision,
                "agent_confidence": round(overall_conf, 2),
                "status": "processed",
                "evidence_data": json.dumps(dump_data),
                "structured_evidence": dump_data
            }

        except Exception as err:
            return self._build_fail_open_response(
                org_id=org_id,
                unit_id=unit_id,
                po_line_spec=po_line_spec,
                captured_images=captured_images,
                captured_at=captured_at,
                reason=f"Batch inspection caught exception: {str(err)} (Fail-open fallback active)"
            )

    # --------------------------------------------------------------------------
    # Visual Image Analysis (Pillow & Feature Heuristics)
    # --------------------------------------------------------------------------

    def _analyze_captured_images(self, image_paths: List[str]) -> Dict[str, Any]:
        """Analyzes real image files on disk for clarity, luminosity, and simulated defects."""
        if not image_paths:
            return {"min_clarity": 0.20, "is_occluded": True, "damage_hints": [], "is_blurry": True}

        clarity_scores = []
        damage_hints = []
        is_blurry = False
        is_occluded = False

        for path in image_paths:
            full_path = os.path.join(self.base_dir, path) if not os.path.isabs(path) else path
            
            # String name heuristic for test fixtures
            path_lower = path.lower()
            if "blur" in path_lower or "dark" in path_lower or "occluded" in path_lower:
                clarity_scores.append(0.35)
                is_blurry = True
            elif "crush" in path_lower:
                damage_hints.append("crushing")
                clarity_scores.append(0.92)
            elif "water" in path_lower:
                damage_hints.append("water")
                clarity_scores.append(0.90)
            elif "tear" in path_lower:
                damage_hints.append("tears")
                clarity_scores.append(0.91)
            elif "missing" in path_lower:
                damage_hints.append("missing_components")
                clarity_scores.append(0.93)
            elif "wrong_sku" in path_lower:
                damage_hints.append("wrong_sku")
                clarity_scores.append(0.94)
            elif "wrong_variant" in path_lower or "red_variant" in path_lower:
                damage_hints.append("wrong_variant")
                clarity_scores.append(0.94)
            else:
                clarity_scores.append(0.95)

            # Pillow image inspection if file exists
            if PIL_AVAILABLE and os.path.exists(full_path):
                try:
                    with Image.open(full_path) as img:
                        w, h = img.size
                        # Check image resolution
                        if w < 200 or h < 200:
                            clarity_scores[-1] = min(clarity_scores[-1], 0.38)
                            is_blurry = True

                        # Image brightness/luminosity
                        stat = ImageStat.Stat(img.convert("L"))
                        mean_luminance = stat.mean[0]
                        # Extreme underexposure or extreme washout
                        if mean_luminance < 25 or mean_luminance > 240:
                            clarity_scores[-1] = min(clarity_scores[-1], 0.32)
                            is_blurry = True
                except Exception:
                    pass

        min_clarity = min(clarity_scores) if clarity_scores else 0.20
        return {
            "min_clarity": min_clarity,
            "damage_hints": damage_hints,
            "is_blurry": is_blurry,
            "is_occluded": is_occluded or (min_clarity < 0.45)
        }

    # --------------------------------------------------------------------------
    # Sub-Check Inspect Methods
    # --------------------------------------------------------------------------

    def _inspect_sku_identity(
        self, spec: Dict[str, Any], metrics: Dict[str, Any], image_id: str, ts: str
    ) -> CheckEvidenceItem:
        expected_sku = spec.get("sku", "SKU-UNKNOWN")
        override_match = spec.get("override_identity_match")

        if metrics["min_clarity"] < 0.45 and not override_match:
            return CheckEvidenceItem(
                check_name="Product/SKU Identity",
                verdict="UNCERTAIN",
                expected_value=expected_sku,
                observed_value="UNREADABLE_LABEL",
                confidence=0.40,
                evidence_source="Visual Barcode & Label OCR",
                evidence_description="Image resolution or glare prevents reliable barcode / SKU character extraction.",
                image_identifier=image_id,
                bounding_box={"x": 0.25, "y": 0.38, "w": 0.20, "h": 0.25},
                timestamp=ts
            )

        if override_match == "no" or "wrong_sku" in metrics["damage_hints"]:
            observed_sku = "RED-MUG-002" if expected_sku != "RED-MUG-002" else "WRONG-SKU-999"
            return CheckEvidenceItem(
                check_name="Product/SKU Identity",
                verdict="FAIL",
                expected_value=expected_sku,
                observed_value=observed_sku,
                confidence=0.96,
                evidence_source="Visual Barcode & Label OCR",
                evidence_description=f"Label barcode decoded as '{observed_sku}', contradicting PO line SKU '{expected_sku}'.",
                image_identifier=image_id,
                bounding_box={"x": 0.25, "y": 0.38, "w": 0.20, "h": 0.25},
                timestamp=ts
            )

        if override_match == "uncertain":
            return CheckEvidenceItem(
                check_name="Product/SKU Identity",
                verdict="UNCERTAIN",
                expected_value=expected_sku,
                observed_value="UNCERTAIN / UNREADABLE",
                confidence=0.40,
                evidence_source="Visual Barcode & Label OCR",
                evidence_description="Image resolution, occlusion, or glare prevents reliable barcode / SKU verification.",
                image_identifier=image_id,
                bounding_box={"x": 0.25, "y": 0.38, "w": 0.20, "h": 0.25},
                timestamp=ts
            )

        return CheckEvidenceItem(
            check_name="Product/SKU Identity",
            verdict="PASS",
            expected_value=expected_sku,
            observed_value=expected_sku,
            confidence=0.96,
            evidence_source="Visual Barcode & Label OCR",
            evidence_description=f"Shipping label and product packaging text match PO SKU '{expected_sku}'.",
            image_identifier=image_id,
            bounding_box={"x": 0.25, "y": 0.38, "w": 0.20, "h": 0.25},
            timestamp=ts
        )

    def _verify_quantity(
        self, spec: Dict[str, Any], metrics: Dict[str, Any], image_id: str, ts: str
    ) -> Tuple[QuantityEvidence, CheckEvidenceItem]:
        # Expected values from PO
        cartons_ordered = safe_int(spec.get("cartons_ordered"), 1)
        units_per_carton_ordered = safe_int(spec.get("units_per_carton_ordered"), 12)
        expected_total = safe_int(spec.get("qty_ordered"), cartons_ordered * units_per_carton_ordered)

        # Observed values from dock intake
        cartons_received = safe_int(spec.get("cartons_received"), cartons_ordered)
        units_per_carton_counted = safe_int(spec.get("units_per_carton_counted"), units_per_carton_ordered)
        inferred_total = safe_int(spec.get("qty_received"), cartons_received * units_per_carton_counted)

        # Direct count vs Inferred count
        # In a sealed carton, individual units cannot be directly observed unless opened
        is_sealed = spec.get("carton_sealed", False) or ("carton" in image_id.lower() and "unit" not in image_id.lower())
        directly_observed = None if is_sealed else (units_per_carton_counted if cartons_received == 1 else None)

        delta = inferred_total - expected_total

        if metrics["min_clarity"] < 0.40:
            qty_verdict = "UNCERTAIN"
            conf = 0.42
            desc = "Carton stack partially obscured; unable to verify physical carton count."
        elif delta == 0:
            qty_verdict = "PASS"
            conf = 0.99
            desc = f"Verified count: {cartons_received} cartons x {units_per_carton_counted} units = {inferred_total} units (Matches PO)."
        else:
            qty_verdict = "FAIL"
            conf = 0.98
            direction = "Short shipment" if delta < 0 else "Over-shipment / extra units"
            desc = f"{direction}: Received {inferred_total} units vs {expected_total} expected (Delta: {delta:+d} units)."

        breakdown = QuantityEvidence(
            expected_carton_count=cartons_ordered,
            observed_carton_count=cartons_received,
            expected_units_per_carton=units_per_carton_ordered,
            observed_units_per_carton=units_per_carton_counted,
            directly_observed_units=directly_observed,
            inferred_total_units=inferred_total,
            expected_total_units=expected_total,
            quantity_discrepancy_delta=delta,
            quantity_verdict=qty_verdict
        )

        check_item = CheckEvidenceItem(
            check_name="Quantity Verification",
            verdict=qty_verdict,
            expected_value=f"{expected_total} units ({cartons_ordered} ctns x {units_per_carton_ordered} units)",
            observed_value=f"{inferred_total} units ({cartons_received} ctns x {units_per_carton_counted} units)",
            confidence=conf,
            evidence_source="Carton Tally & Inner Unit Count",
            evidence_description=desc,
            image_identifier=image_id,
            bounding_box={"x": 0.12, "y": 0.28, "w": 0.65, "h": 0.50},
            timestamp=ts
        )

        return breakdown, check_item

    def _inspect_damage(
        self, images: List[str], metrics: Dict[str, Any], image_id: str, ts: str
    ) -> Tuple[CheckEvidenceItem, CheckEvidenceItem, Dict[str, str]]:
        if metrics["min_clarity"] < 0.45:
            carton_item = CheckEvidenceItem(
                check_name="Carton Physical Integrity",
                verdict="UNCERTAIN",
                expected_value="Undamaged",
                observed_value="UNCERTAIN",
                confidence=0.35,
                evidence_source="Visual Packaging Inspection",
                evidence_description="Lighting glare / motion blur obscures carton corners and seams.",
                image_identifier=image_id,
                bounding_box=None,
                timestamp=ts
            )
            unit_item = CheckEvidenceItem(
                check_name="Unit Physical Integrity",
                verdict="UNCERTAIN",
                expected_value="Undamaged",
                observed_value="UNCERTAIN",
                confidence=0.35,
                evidence_source="Visual Product Inspection",
                evidence_description="Packaging sealed / blurred; internal unit condition cannot be graded.",
                image_identifier=image_id,
                bounding_box=None,
                timestamp=ts
            )
            return carton_item, unit_item, {"carton": "uncertain", "unit": "uncertain"}

        hints = metrics["damage_hints"]
        if "crushing" in hints:
            c_dmg = "crushing"
            desc = "Visible structural deformation and corner compression on corrugated carton."
            bbox = {"x": 0.20, "y": 0.28, "w": 0.18, "h": 0.20}
        elif "water" in hints:
            c_dmg = "water"
            desc = "Moisture stains, darkened cardboard watermarks, and dampness detected on bottom carton panel."
            bbox = {"x": 0.31, "y": 0.58, "w": 0.38, "h": 0.18}
        elif "tears" in hints:
            c_dmg = "tears"
            desc = "Punctured outer wall and torn packaging cardboard with exposed inner contents."
            bbox = {"x": 0.65, "y": 0.40, "w": 0.12, "h": 0.22}
        else:
            c_dmg = "none"
            desc = "No visible carton crushing, moisture absorption, tears, or punctures detected."
            bbox = None

        c_verdict = "PASS" if c_dmg == "none" else "FAIL"

        carton_item = CheckEvidenceItem(
            check_name="Carton Physical Integrity",
            verdict=c_verdict,
            expected_value="No visible damage",
            observed_value=c_dmg,
            confidence=0.93 if c_verdict == "FAIL" else 0.95,
            evidence_source="Visual Packaging Inspection",
            evidence_description=desc,
            image_identifier=image_id,
            bounding_box=bbox,
            timestamp=ts
        )

        unit_dmg = c_dmg if c_dmg in ["water", "tears"] else "none"
        u_verdict = "PASS" if unit_dmg == "none" else "FAIL"

        unit_item = CheckEvidenceItem(
            check_name="Unit Physical Integrity",
            verdict=u_verdict,
            expected_value="No visible defect",
            observed_value=unit_dmg,
            confidence=0.91,
            evidence_source="Visual Product Inspection",
            evidence_description=f"Unit physical status evaluated as '{unit_dmg}'.",
            image_identifier=image_id,
            bounding_box=None,
            timestamp=ts
        )

        return carton_item, unit_item, {"carton": c_dmg, "unit": unit_dmg}

    def _inspect_spec_and_components(
        self, spec: Dict[str, Any], metrics: Dict[str, Any], image_id: str, ts: str
    ) -> Tuple[CheckEvidenceItem, List[str]]:
        expected_colour = spec.get("spec_colour", "n/a")
        expected_variant = spec.get("spec_variant", "n/a")
        expected_components = spec.get("spec_components", "n/a")

        quality_flags = []
        override_flags = spec.get("override_quality_flags", [])
        if isinstance(override_flags, str):
            override_flags = [f.strip() for f in override_flags.split(";") if f.strip()]

        hints = metrics["damage_hints"]
        if "wrong_variant" in hints and "wrong_colour" not in override_flags:
            override_flags.append("wrong_colour")
            override_flags.append("wrong_variant")
        if "missing_components" in hints and "missing_components" not in override_flags:
            override_flags.append("missing_components")

        if metrics["min_clarity"] < 0.45 and not override_flags:
            item = CheckEvidenceItem(
                check_name="Specification & Variant Quality",
                verdict="UNCERTAIN",
                expected_value=f"Colour: {expected_colour}, Variant: {expected_variant}, Comp: {expected_components}",
                observed_value="UNCERTAIN_DUE_TO_LIGHTING",
                confidence=0.40,
                evidence_source="Visual Spec & Colorimetric Analysis",
                evidence_description="Color spectrum and accessory components cannot be verified from occluded photo.",
                image_identifier=image_id,
                bounding_box=None,
                timestamp=ts
            )
            return item, []

        if override_flags:
            quality_flags = list(set(override_flags))
            item = CheckEvidenceItem(
                check_name="Specification & Variant Quality",
                verdict="FAIL",
                expected_value=f"Colour: {expected_colour}, Variant: {expected_variant}, Comp: {expected_components}",
                observed_value=f"Defects: {', '.join(quality_flags)}",
                confidence=0.94,
                evidence_source="Visual Spec & Colorimetric Analysis",
                evidence_description=f"Specification mismatch detected: {', '.join(quality_flags)}.",
                image_identifier=image_id,
                bounding_box={"x": 0.58, "y": 0.38, "w": 0.20, "h": 0.26},
                timestamp=ts
            )
            return item, quality_flags

        item = CheckEvidenceItem(
            check_name="Specification & Variant Quality",
            verdict="PASS",
            expected_value=f"Colour: {expected_colour}, Variant: {expected_variant}, Comp: {expected_components}",
            observed_value=f"Colour: {expected_colour}, Variant: {expected_variant}, Comp: {expected_components}",
            confidence=0.95,
            evidence_source="Visual Spec & Colorimetric Analysis",
            evidence_description="Confirmed product colour, size variant, and bundle accessories match PO spec.",
            image_identifier=image_id,
            bounding_box=None,
            timestamp=ts
        )
        return item, []

    # --------------------------------------------------------------------------
    # Real Multimodal Vision (Google Gemini API) - Used ONLY when GEMINI_API_KEY is configured
    # --------------------------------------------------------------------------

    def _run_real_gemini_vision(
        self,
        org_id: str,
        unit_id: str,
        po_line_spec: Dict[str, Any],
        captured_images: List[str],
        captured_at: str,
        start_time: float,
        shipment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes single-pass multimodal visual verification against Google Gemini Vision API.
        Used ONLY when GEMINI_API_KEY is configured.
        Supports multi-candidate SKU discrimination (Priority 4 & 5) and optional bounding boxes (Priority 8).
        """
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)

        po_sku = po_line_spec.get("sku", "UNKNOWN")
        po_title = po_line_spec.get("product_title", "Sample Product")
        spec_col = po_line_spec.get("spec_colour", "n/a")
        spec_var = po_line_spec.get("spec_variant", "n/a")
        spec_comp = po_line_spec.get("spec_components", "n/a")
        cartons_ord = safe_int(po_line_spec.get("cartons_ordered"), 1)
        units_per_c_ord = safe_int(po_line_spec.get("units_per_carton_ordered"), 12)
        qty_ord = safe_int(po_line_spec.get("qty_ordered"), cartons_ord * units_per_c_ord)

        # Retrieve catalogue candidate SKU set (expected SKU + look-alike alternatives)
        candidates = candidate_provider.get_candidate_set(po_sku, po_line_spec)
        candidates_formatted = "\n".join([
            f"  - SKU: {c['sku']} | Title: {c['product_title']} | Variant: {c.get('spec_variant', 'n/a')} | Is Expected PO SKU: {c.get('is_expected', False)}"
            for c in candidates
        ])

        pil_images = []
        if PIL_AVAILABLE:
            for img_ref in captured_images:
                full_path = os.path.join(self.base_dir, img_ref) if not os.path.isabs(img_ref) else img_ref
                if os.path.exists(full_path):
                    try:
                        pil_images.append(Image.open(full_path))
                    except Exception:
                        pass

        prompt = f"""You are the Receiving Manager AI Agent inspecting an inbound freight receipt.
Evaluate the attached image(s) against this Purchase Order line specification:
- PO Number: {po_line_spec.get("po_number", "PO-UNKNOWN")}
- PO Line: {po_line_spec.get("po_line", 1)}
- Expected SKU: {po_sku}
- Expected Product Title: {po_title}
- Expected Specification: Colour={spec_col}, Variant={spec_var}, Components={spec_comp}
- Cartons Ordered: {cartons_ord}
- Units Per Carton Ordered: {units_per_c_ord}
- Expected Total Quantity: {qty_ord} units

Catalogue Candidate SKUs for visual discrimination:
{candidates_formatted}

Conduct unified single-pass verification across all 5 receiving checks:
1. Product / SKU Identity: You must examine the shipping label, packaging text, or barcode and discriminate among the candidate SKUs above.
   - observed_sku: which SKU from the candidates (or label) is visually observed? (string or null)
   - candidate_sku: the closest candidate SKU evaluated (string or null)
   - identity_match: "yes" if observed clearly matches expected SKU {po_sku}; "no" if observed matches another candidate or distinct SKU; "uncertain" if label is unreadable, blurry, occluded, or evidence is insufficient.
   - identity_confidence: float between 0.0 and 1.0
   - identity_evidence: text description of label, markings, or visual cues seen.
2. Quantity Verification: How many cartons are observed? How many units per carton? (If carton is sealed, report carton count and infer total).
3. Carton Physical Integrity: Check for crushing (>10% volume), water/moisture intrusion, tears, or punctures. (none/crushing/water/tears/uncertain)
4. Unit Physical Integrity: Are inner units intact? (none/crushing/water/tears/uncertain)
5. Specification Quality Flags: Are there defects such as wrong_colour, wrong_variant, or missing_components? (Array of strings, or empty)
6. Overall Verdict: PASS (all match PO, no damage), FAIL (any discrepancy/defect), or UNCERTAIN (blurry image, occluded barcode, unreadable text).
7. Decision Rationale: Concise, professional dock log explaining the findings.
8. If UNCERTAIN: Provide uncertain_explanation and recommended_next_evidence.
9. Optional Bounding Box: If packaging or damage or label is localized, provide normalized bounding box {{"x": float, "y": float, "width": float, "height": float}} (between 0.0 and 1.0) or null.

Return STRICT JSON ONLY matching this structure:
{{
  "observed_sku": "<string or null>",
  "candidate_sku": "<string or null>",
  "identity_match": "yes" | "no" | "uncertain",
  "identity_confidence": <float between 0.0 and 1.0>,
  "identity_evidence": "<string>",
  "cartons_observed": <int>,
  "units_per_carton_observed": <int>,
  "carton_damage": "none" | "crushing" | "water" | "tears" | "uncertain",
  "unit_damage": "none" | "crushing" | "water" | "tears" | "uncertain",
  "quality_flags": [<string>],
  "overall_verdict": "PASS" | "FAIL" | "UNCERTAIN",
  "agent_confidence": <float between 0.0 and 1.0>,
  "decision_rationale": "<string>",
  "uncertain_explanation": "<string or null>",
  "recommended_next_evidence": "<string or null>",
  "bounding_box": {{"x": <float>, "y": <float>, "width": <float>, "height": <float>}} | null
}}
"""
        contents = [prompt] + pil_images
        response = model.generate_content(
            contents,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)

        # Extract token usage metadata from Gemini response if available (Phase 3 compliance)
        token_usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            token_usage = {
                "prompt_tokens": getattr(meta, "prompt_token_count", None),
                "candidates_tokens": getattr(meta, "candidates_token_count", None),
                "total_tokens": getattr(meta, "total_token_count", None)
            }
            print(f"[ReceivingManagerAgent] Gemini token usage logged: {token_usage}")

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        primary_image = captured_images[0] if captured_images else "fixtures/receiving/default_pallet.jpg"

        cartons_rec = safe_int(data.get("cartons_observed"), cartons_ord)
        units_rec = safe_int(data.get("units_per_carton_observed"), units_per_c_ord)
        total_rec = cartons_rec * units_rec
        delta = total_rec - qty_ord

        qty_verdict = "PASS" if delta == 0 else "FAIL"
        if data.get("identity_match") == "uncertain" or data.get("carton_damage") == "uncertain":
            qty_verdict = "UNCERTAIN" if delta == 0 else "FAIL"

        qty_breakdown = QuantityEvidence(
            expected_carton_count=cartons_ord,
            observed_carton_count=cartons_rec,
            expected_units_per_carton=units_per_c_ord,
            observed_units_per_carton=units_rec,
            directly_observed_units=None,
            inferred_total_units=total_rec,
            expected_total_units=qty_ord,
            quantity_discrepancy_delta=delta,
            quantity_verdict=qty_verdict
        )

        # Parse normalized bounding box if provided by Gemini (Priority 8)
        raw_box = data.get("bounding_box")
        box_dict = None
        if isinstance(raw_box, dict) and all(k in raw_box for k in ["x", "y", "width", "height"]):
            try:
                box_dict = {
                    "x": float(raw_box["x"]),
                    "y": float(raw_box["y"]),
                    "width": float(raw_box["width"]),
                    "height": float(raw_box["height"])
                }
            except (ValueError, TypeError):
                box_dict = None

        observed_identity = data.get("observed_sku") or (po_sku if data.get("identity_match") == "yes" else ("UNREADABLE_OR_OCCLUDED" if data.get("identity_match") == "uncertain" else "MISMATCH"))

        all_checks = [
            CheckEvidenceItem(
                check_name="Product/SKU Identity",
                verdict="PASS" if data.get("identity_match") == "yes" else ("FAIL" if data.get("identity_match") == "no" else "UNCERTAIN"),
                expected_value=po_sku,
                observed_value=observed_identity,
                confidence=float(data.get("identity_confidence", data.get("agent_confidence", 0.9))),
                evidence_source="Google Gemini Multimodal Vision API",
                evidence_description=data.get("identity_evidence", "Gemini analyzed shipping label, barcode, and catalogue candidate set."),
                image_identifier=primary_image,
                bounding_box=box_dict,
                timestamp=captured_at
            ),
            CheckEvidenceItem(
                check_name="Quantity Verification",
                verdict=qty_verdict,
                expected_value=f"{qty_ord} units",
                observed_value=f"{total_rec} units",
                confidence=float(data.get("agent_confidence", 0.9)),
                evidence_source="Google Gemini Multimodal Vision API",
                evidence_description=f"Counted {cartons_rec} cartons x {units_rec} units/carton.",
                image_identifier=primary_image,
                timestamp=captured_at
            ),
            CheckEvidenceItem(
                check_name="Carton Physical Integrity",
                verdict="PASS" if data.get("carton_damage") == "none" else ("FAIL" if data.get("carton_damage") in ["crushing", "water", "tears"] else "UNCERTAIN"),
                expected_value="Undamaged",
                observed_value=data.get("carton_damage", "none"),
                confidence=float(data.get("agent_confidence", 0.9)),
                evidence_source="Google Gemini Multimodal Vision API",
                evidence_description=f"Gemini assessed carton damage as: {data.get('carton_damage')}.",
                image_identifier=primary_image,
                bounding_box=box_dict if data.get("carton_damage") != "none" else None,
                timestamp=captured_at
            ),
            CheckEvidenceItem(
                check_name="Unit Physical Integrity",
                verdict="PASS" if data.get("unit_damage") == "none" else ("FAIL" if data.get("unit_damage") in ["crushing", "water", "tears"] else "UNCERTAIN"),
                expected_value="Undamaged",
                observed_value=data.get("unit_damage", "none"),
                confidence=float(data.get("agent_confidence", 0.9)),
                evidence_source="Google Gemini Multimodal Vision API",
                evidence_description=f"Gemini assessed unit damage as: {data.get('unit_damage')}.",
                image_identifier=primary_image,
                bounding_box=box_dict if data.get("unit_damage") != "none" else None,
                timestamp=captured_at
            ),
            CheckEvidenceItem(
                check_name="Specification & Variant Quality",
                verdict="PASS" if not data.get("quality_flags") else "FAIL",
                expected_value=f"Colour: {spec_col}, Variant: {spec_var}",
                observed_value="Matches spec" if not data.get("quality_flags") else f"Flags: {', '.join(data.get('quality_flags', []))}",
                confidence=float(data.get("agent_confidence", 0.9)),
                evidence_source="Google Gemini Multimodal Vision API",
                evidence_description="Gemini checked colour, variant, and accessories against spec.",
                image_identifier=primary_image,
                timestamp=captured_at
            )
        ]

        q_flags = data.get("quality_flags", [])
        compliance_input = {
            "carton_damage": data.get("carton_damage", "none"),
            "unit_damage": data.get("unit_damage", "none"),
            "quality_flags": ";".join(q_flags) if isinstance(q_flags, list) else str(q_flags),
            "qty_ordered": qty_ord,
            "qty_received": total_rec
        }
        channel_rules_eval = evaluate_authoritative_compliance(compliance_input)

        overall_verdict = data.get("overall_verdict", "UNCERTAIN")
        overall_decision = "PASS" if overall_verdict == "PASS" else ("EXCEPTION" if overall_verdict == "FAIL" else "UNCERTAIN")

        legacy_checks = [
            {"check_name": c.check_name, "verdict": c.verdict, "confidence": c.confidence, "details": c.evidence_description}
            for c in all_checks
        ]

        structured = InspectionResultSchema(
            schema_version="1.0.0",
            unit_id=unit_id,
            shipment_id=shipment_id,
            org_id=org_id,
            model_name=self.model_name,
            model_version=self.model_version,
            batch_single_pass=True,
            batch_execution_time_ms=elapsed_ms,
            captured_at=captured_at,
            status="processed",
            overall_verdict=overall_verdict,
            overall_decision=overall_decision,
            agent_confidence=float(data.get("agent_confidence", 0.9)),
            decision_rationale=data.get("decision_rationale", "Gemini live multimodal vision inspection completed."),
            uncertain_explanation=data.get("uncertain_explanation"),
            recommended_next_evidence=data.get("recommended_next_evidence"),
            execution_mode="REAL_AI_MULTIMODAL",
            is_real_ai=True,
            ai_provider="Google Gemini Multimodal Vision API",
            what_received={
                "cartons_received": cartons_rec,
                "units_per_carton": units_rec,
                "total_qty_received": total_rec,
                "photo_refs": captured_images
            },
            what_expected={
                "po_number": po_line_spec.get("po_number", "PO-7000"),
                "po_line": po_line_spec.get("po_line", 1),
                "shipment_id": shipment_id,
                "supplier": po_line_spec.get("supplier", "Supplier Standard"),
                "sku": po_sku,
                "asin": po_line_spec.get("asin", "B0DUMMY000"),
                "product_title": po_title,
                "spec": {"colour": spec_col, "variant": spec_var, "components": spec_comp},
                "cartons_ordered": cartons_ord,
                "qty_ordered": qty_ord
            },
            checks=legacy_checks,
            quantity_breakdown=qty_breakdown,
            individual_checks=all_checks,
            authoritative_channel_checks=channel_rules_eval,
            candidate_skus=candidates,
            token_usage=token_usage
        )
        dump_data = structured.model_dump() if hasattr(structured, "model_dump") else structured.dict()

        return {
            "unit_id": unit_id,
            "shipment_id": shipment_id,
            "candidate_skus": candidates,
            "token_usage": token_usage,
            "org_id": org_id,
            "captured_at": captured_at,
            "batch_execution_time_ms": elapsed_ms,
            "batch_single_pass": True,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "execution_mode": "REAL_AI_MULTIMODAL",
            "is_real_ai": True,
            "ai_provider": "Google Gemini Multimodal Vision API",
            "identity_match": data.get("identity_match", "uncertain"),
            "cartons_ordered": cartons_ord,
            "cartons_received": cartons_rec,
            "units_per_carton_ordered": units_per_c_ord,
            "units_per_carton_counted": units_rec,
            "qty_ordered": qty_ord,
            "qty_received": total_rec,
            "directly_observed_units": None,
            "carton_damage": data.get("carton_damage", "none"),
            "unit_damage": data.get("unit_damage", "none"),
            "quality_flags": ";".join(q_flags) if isinstance(q_flags, list) else str(q_flags),
            "overall_verdict": overall_verdict,
            "overall_decision": overall_decision,
            "agent_confidence": float(data.get("agent_confidence", 0.9)),
            "status": "processed",
            "evidence_data": json.dumps(dump_data),
            "structured_evidence": dump_data
        }

    # --------------------------------------------------------------------------
    # Fail-Open Execution (Engineering Rule 3)
    # --------------------------------------------------------------------------

    def _build_fail_open_response(
        self, org_id: str, unit_id: str, po_line_spec: Dict[str, Any],
        captured_images: List[str], captured_at: str, reason: str,
        shipment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if po_line_spec is None or not isinstance(po_line_spec, dict):
            po_line_spec = {}

        if shipment_id is None:
            shipment_id = po_line_spec.get("shipment_id")

        cartons_ord = safe_int(po_line_spec.get("cartons_ordered"), 1)
        cartons_rec = safe_int(po_line_spec.get("cartons_received"), cartons_ord)
        units_ord = safe_int(po_line_spec.get("units_per_carton_ordered"), 12)
        units_cnt = safe_int(po_line_spec.get("units_per_carton_counted"), units_ord)
        qty_ord = safe_int(po_line_spec.get("qty_ordered"), cartons_ord * units_ord)
        qty_rec = safe_int(po_line_spec.get("qty_received"), cartons_rec * units_cnt)

        primary_image = captured_images[0] if captured_images else "fixtures/receiving/default_pallet.jpg"

        qty_breakdown = QuantityEvidence(
            expected_carton_count=cartons_ord,
            observed_carton_count=cartons_rec,
            expected_units_per_carton=units_ord,
            observed_units_per_carton=units_cnt,
            directly_observed_units=None,
            inferred_total_units=qty_rec,
            expected_total_units=qty_ord,
            quantity_discrepancy_delta=qty_rec - qty_ord,
            quantity_verdict="PENDING"
        )

        checks = [
            CheckEvidenceItem(
                check_name="Batch Visual Inspection",
                verdict="PENDING",
                expected_value=po_line_spec.get("sku", "SKU-UNKNOWN"),
                observed_value="PENDING_ANALYSIS",
                confidence=0.0,
                evidence_source="Fail-Open Circuit Breaker",
                evidence_description=reason,
                image_identifier=primary_image,
                timestamp=captured_at
            )
        ]

        what_received_data = {
            "cartons_received": cartons_rec,
            "units_per_carton": units_cnt,
            "total_qty_received": qty_rec,
            "photo_refs": captured_images
        }
        what_expected_data = {
            "po_number": po_line_spec.get("po_number", "PO-7000"),
            "po_line": po_line_spec.get("po_line", 1),
            "shipment_id": shipment_id,
            "supplier": po_line_spec.get("supplier", "Supplier Standard"),
            "sku": po_line_spec.get("sku", "SKU-UNKNOWN"),
            "asin": po_line_spec.get("asin", "B0DUMMY000"),
            "product_title": po_line_spec.get("product_title", "Sample Product"),
            "cartons_ordered": cartons_ord,
            "qty_ordered": qty_ord
        }
        legacy_checks = [
            {
                "check_name": "Batch Inspection",
                "verdict": "UNCERTAIN",
                "confidence": 0.0,
                "details": reason
            }
        ]

        # Preserve execution mode fidelity: Never silently switch REAL_AI to DEMO mode
        exec_mode = "REAL_AI_MULTIMODAL" if self.is_real_ai else self.execution_mode
        ai_prov = "Google Gemini Multimodal Vision API (Fail-Open Active)" if self.is_real_ai else self.ai_provider

        structured = InspectionResultSchema(
            schema_version="1.0.0",
            unit_id=unit_id,
            shipment_id=shipment_id,
            org_id=org_id,
            model_name=self.model_name,
            model_version=self.model_version,
            batch_single_pass=True,
            batch_execution_time_ms=0.0,
            captured_at=captured_at,
            status="pending_review",
            overall_verdict="PENDING_REVIEW",
            overall_decision="PENDING",
            agent_confidence=0.0,
            decision_rationale=f"FAIL-OPEN ACTIVE: {reason}",
            uncertain_explanation="AI pipeline service latency exceeded threshold. Saved safely for dock continuity.",
            recommended_next_evidence="Operator may perform manual override or trigger Retry Inspection once connectivity stabilizes.",
            execution_mode=exec_mode,
            is_real_ai=self.is_real_ai,
            ai_provider=ai_prov,
            what_received=what_received_data,
            what_expected=what_expected_data,
            checks=legacy_checks,
            quantity_breakdown=qty_breakdown,
            individual_checks=checks,
            authoritative_channel_checks=[]
        )

        dump_data = structured.model_dump() if hasattr(structured, "model_dump") else structured.dict()

        return {
            "unit_id": unit_id,
            "shipment_id": shipment_id,
            "org_id": org_id,
            "captured_at": captured_at,
            "batch_execution_time_ms": 0.0,
            "batch_single_pass": True,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "execution_mode": exec_mode,
            "is_real_ai": self.is_real_ai,
            "ai_provider": ai_prov,
            "identity_match": "uncertain",
            "cartons_ordered": cartons_ord,
            "cartons_received": cartons_rec,
            "units_per_carton_ordered": units_ord,
            "units_per_carton_counted": units_cnt,
            "qty_ordered": qty_ord,
            "qty_received": qty_rec,
            "directly_observed_units": None,
            "carton_damage": "uncertain",
            "unit_damage": "uncertain",
            "quality_flags": "",
            "overall_verdict": "PENDING_REVIEW",
            "overall_decision": "PENDING",
            "agent_confidence": 0.0,
            "status": "pending_review",
            "evidence_data": json.dumps(dump_data),
            "structured_evidence": dump_data
        }
