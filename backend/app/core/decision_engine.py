"""Deterministic business rules for receiving inspections."""

from __future__ import annotations

from typing import Literal

Decision = Literal["PASS", "EXCEPTION", "UNCERTAIN"]


def _normalize(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"", "unknown", "n/a", "uncertain", "not_available"}:
            return None
        return cleaned
    return value


def evaluate_overall(checks: list[dict]) -> Decision:
    """Return the overall verdict based on the current check states."""
    if not checks:
        return "UNCERTAIN"

    if any(str(check.get("status", "UNCERTAIN")).upper() == "FAIL" for check in checks):
        return "EXCEPTION"

    if any(str(check.get("status", "UNCERTAIN")).upper() == "UNCERTAIN" for check in checks):
        return "UNCERTAIN"

    return "PASS"


def evaluate_sku_check(expected_sku, observed_sku):
    expected = _normalize(expected_sku)
    observed = _normalize(observed_sku)

    if expected is None:
        return {"status": "UNCERTAIN", "reason": "Expected SKU information is missing."}
    if observed is None:
        return {"status": "UNCERTAIN", "reason": "Observed SKU is unavailable because the evidence is insufficient."}
    if observed == expected:
        return {"status": "PASS", "reason": "Observed SKU matches the expected SKU."}
    return {"status": "FAIL", "reason": f"SKU mismatch: expected {expected_sku}, observed {observed_sku}."}


def evaluate_quantity_check(expected_quantity, observed_quantity):
    expected = expected_quantity
    observed = observed_quantity

    if expected is None:
        return {"status": "UNCERTAIN", "reason": "Expected quantity is missing."}
    if observed is None:
        return {"status": "UNCERTAIN", "reason": "Observed quantity is unavailable because the evidence is insufficient."}
    if int(observed) < 0:
        return {"status": "UNCERTAIN", "reason": "Observed quantity is invalid."}

    if int(observed) == int(expected):
        return {"status": "PASS", "reason": "Observed quantity matches the expected quantity."}

    return {
        "status": "FAIL",
        "reason": f"Quantity mismatch: expected {expected}, observed {observed}.",
    }


def evaluate_carton_check(expected_cartons, observed_cartons):
    if expected_cartons is None:
        return {"status": "UNCERTAIN", "reason": "Expected carton count is missing."}
    if observed_cartons is None:
        return {"status": "UNCERTAIN", "reason": "Observed carton count is unavailable because the evidence is insufficient."}

    if int(observed_cartons) == int(expected_cartons):
        return {"status": "PASS", "reason": "Observed carton count matches the expected carton count."}

    return {
        "status": "FAIL",
        "reason": f"Carton count mismatch: expected {expected_cartons}, observed {observed_cartons}.",
    }


def evaluate_variant_check(expected_variant, observed_variant):
    expected = _normalize(expected_variant)
    observed = _normalize(observed_variant)

    if expected is None:
        return {"status": "UNCERTAIN", "reason": "Expected variant information is missing."}
    if observed is None:
        return {"status": "UNCERTAIN", "reason": "Observed variant is unavailable because the evidence is insufficient."}

    if observed == expected:
        return {"status": "PASS", "reason": "Observed variant matches the expected variant."}

    return {"status": "FAIL", "reason": f"Variant mismatch: expected {expected_variant}, observed {observed_variant}."}


def evaluate_damage_check(observed_damage):
    if observed_damage is None:
        return {"status": "UNCERTAIN", "reason": "Damage status is unavailable because the evidence is insufficient."}
    if isinstance(observed_damage, list):
        if not observed_damage:
            return {"status": "PASS", "reason": "No visible damage was detected."}
        normalized = [_normalize(item) for item in observed_damage]
        if any(item in {"uncertain", "unknown", "not_visible"} for item in normalized if item is not None):
            return {"status": "UNCERTAIN", "reason": "Damage status could not be verified from the evidence."}
        if any(item not in {None, "none", "no_damage", "", "not_visible"} for item in normalized):
            return {"status": "FAIL", "reason": f"Visible damage detected: {observed_damage}."}
        return {"status": "PASS", "reason": "No visible damage was detected."}

    normalized = _normalize(observed_damage)
    if normalized in {None, "none", "no_damage"}:
        return {"status": "PASS", "reason": "No visible damage was detected."}
    if normalized in {"uncertain", "unknown", "not_visible"}:
        return {"status": "UNCERTAIN", "reason": "Damage status could not be verified from the evidence."}
    return {"status": "FAIL", "reason": f"Visible damage detected: {observed_damage}."}


def evaluate_component_check(expected_components, observed_components):
    expected = [str(item).strip() for item in (expected_components or []) if str(item).strip()]
    observed = [str(item).strip() for item in (observed_components or []) if str(item).strip()]

    if not expected:
        return {"status": "PASS", "reason": "No expected components were provided."}
    if not observed:
        return {"status": "UNCERTAIN", "reason": "Component presence could not be confirmed from the available evidence."}

    missing = [item for item in expected if item.lower() not in {obs.lower() for obs in observed}]
    if missing:
        return {"status": "FAIL", "reason": f"Missing expected components: {', '.join(missing)}."}
    return {"status": "PASS", "reason": "All expected components are present."}


def evaluate_inspection(checks: list[dict]) -> Decision:
    """Evaluate the set of inspection checks and return the final decision."""
    if not checks:
        return "UNCERTAIN"

    statuses = [str(check.get("status", "UNCERTAIN")).upper() for check in checks]

    if any(status == "FAIL" for status in statuses):
        return "EXCEPTION"
    if any(status == "UNCERTAIN" for status in statuses):
        return "UNCERTAIN"
    return "PASS"
