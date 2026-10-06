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


def _coerce_int(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned == "":
            return None
        normalized = _normalize(cleaned)
        if normalized is None:
            return None
        try:
            return int(float(cleaned))
        except (TypeError, ValueError):
            return None
    return None


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
    expected = _coerce_int(expected_quantity)
    observed = _coerce_int(observed_quantity)

    if expected is None:
        return {"status": "UNCERTAIN", "reason": "Expected quantity is missing."}
    if observed is None:
        return {"status": "UNCERTAIN", "reason": "Observed quantity is unavailable because the evidence is insufficient."}
    if observed < 0:
        return {"status": "UNCERTAIN", "reason": "Observed quantity is invalid."}

    if observed == expected:
        return {"status": "PASS", "reason": "Observed quantity matches the expected quantity."}

    return {
        "status": "FAIL",
        "reason": f"Quantity mismatch: expected {expected}, observed {observed}.",
    }


def evaluate_carton_check(expected_cartons, observed_cartons):
    expected = _coerce_int(expected_cartons)
    observed = _coerce_int(observed_cartons)

    if expected is None:
        return {"status": "UNCERTAIN", "reason": "Expected carton count is missing."}
    if observed is None:
        return {"status": "UNCERTAIN", "reason": "Observed carton count is unavailable because the evidence is insufficient."}

    if observed == expected:
        return {"status": "PASS", "reason": "Observed carton count matches the expected carton count."}

    return {
        "status": "FAIL",
        "reason": f"Carton count mismatch: expected {expected}, observed {observed}.",
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


def _contains_uncertain_damage(observed_damage):
    values = observed_damage if isinstance(observed_damage, (list, tuple, set)) else [observed_damage]
    return any(
        isinstance(item, str)
        and item.strip().lower() in {"uncertain", "unknown", "not_visible", "n/a", "not_available"}
        for item in values
    )


def evaluate_damage_check(observed_damage):
    if observed_damage is None:
        return {"status": "UNCERTAIN", "reason": "Damage status is unavailable because the evidence is insufficient."}

    if _contains_uncertain_damage(observed_damage):
        return {"status": "UNCERTAIN", "reason": "Damage status could not be verified from the evidence."}

    values = observed_damage if isinstance(observed_damage, (list, tuple, set)) else [observed_damage]
    if not values:
        return {"status": "PASS", "reason": "No visible damage was detected."}

    normalized = [_normalize(item) for item in values]
    if any(item not in {None, "none", "no_damage", "", "not_visible"} for item in normalized):
        return {"status": "FAIL", "reason": f"Visible damage detected: {observed_damage}."}
    return {"status": "PASS", "reason": "No visible damage was detected."}


def evaluate_component_check(expected_components, observed_components):
    def _as_component_list(value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, (list, tuple, set)):
            items = []
            for item in value:
                text = str(item).strip()
                if text:
                    items.append(text)
            return items
        text = str(value).strip()
        return [text] if text else []

    expected = _as_component_list(expected_components)
    observed = _as_component_list(observed_components)

    if not expected:
        return {"status": "NOT_REQUIRED", "reason": "No components are required by the purchase order."}
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
