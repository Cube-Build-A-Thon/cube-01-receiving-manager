import os

from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.core.config import get_settings
from backend.app.core.decision_engine import evaluate_inspection
from backend.app.main import app
from backend.app.models.inspection import InspectionCheck

client = TestClient(app)


def _png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"


def _jpeg_bytes() -> bytes:
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00" + b"\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x3f"


def _create_inspection(payload=None):
    default_payload = {
        "po": {
            "po_id": "PO-1001",
            "sku": "BLUE-BOTTLE-001",
            "product_name": "Blue Bottle",
            "expected_quantity": 24,
            "variant": "Blue",
            "units_per_carton": 12,
            "expected_cartons": 2,
            "expected_components": ["cap", "label"],
        }
    }
    response = client.post("/api/inspections", json=payload or default_payload)
    assert response.status_code == 200
    return response.json()


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cors_headers_are_enabled_for_allowed_origin():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_create_inspection():
    data = _create_inspection()
    assert "inspection_id" in data
    assert data["po"]["po_id"] == "PO-1001"


def test_retrieve_inspection():
    data = _create_inspection({"po": {"po_id": "PO-1002", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    response = client.get(f"/api/inspections/{data['inspection_id']}")
    assert response.status_code == 200
    assert response.json()["inspection_id"] == data["inspection_id"]


def test_invalid_quantity():
    payload = {
        "po": {
            "po_id": "PO-1003",
            "sku": "BLUE-BOTTLE-001",
            "product_name": "Blue Bottle",
            "expected_quantity": -1,
            "variant": "Blue",
            "units_per_carton": 12,
            "expected_cartons": 2,
        }
    }

    response = client.post("/api/inspections", json=payload)
    assert response.status_code in {400, 422}


def test_invalid_confidence():
    try:
        InspectionCheck(
            check_name="quantity_check",
            status="PASS",
            expected_value=24,
            observed_value=24,
            reason="ok",
            confidence=1.5,
        )
    except ValidationError:
        return

    assert False, "ValidationError should have been raised for confidence outside 0..1"


def test_pass_decision():
    checks = [
        {"check_name": "sku_check", "status": "PASS", "expected_value": "BLUE-BOTTLE-001", "observed_value": "BLUE-BOTTLE-001", "reason": "match", "confidence": 0.95},
        {"check_name": "quantity_check", "status": "PASS", "expected_value": 24, "observed_value": 24, "reason": "match", "confidence": 0.94},
        {"check_name": "variant_check", "status": "PASS", "expected_value": "Blue", "observed_value": "Blue", "reason": "match", "confidence": 0.96},
        {"check_name": "damage_check", "status": "PASS", "expected_value": "none", "observed_value": "none", "reason": "no visible damage", "confidence": 0.92},
    ]

    result = evaluate_inspection(checks)
    assert result == "PASS"


def test_fail_exception_decision():
    checks = [
        {"check_name": "sku_check", "status": "PASS", "expected_value": "BLUE-BOTTLE-001", "observed_value": "BLUE-BOTTLE-001", "reason": "match", "confidence": 0.95},
        {"check_name": "quantity_check", "status": "FAIL", "expected_value": 24, "observed_value": 22, "reason": "short", "confidence": 0.88},
    ]

    result = evaluate_inspection(checks)
    assert result == "EXCEPTION"


def test_uncertain_decision():
    checks = [
        {"check_name": "sku_check", "status": "UNCERTAIN", "expected_value": "BLUE-BOTTLE-001", "observed_value": None, "reason": "insufficient evidence", "confidence": 0.65},
    ]

    result = evaluate_inspection(checks)
    assert result == "UNCERTAIN"


def test_inspection_not_found():
    response = client.get("/api/inspections/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Inspection not found"


def test_valid_jpeg_upload_and_retrieve():
    inspection = _create_inspection({"po": {"po_id": "PO-2001", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    response = client.post(f"/api/inspections/{inspection['inspection_id']}/images", files=[("files", ("photo.jpg", _jpeg_bytes(), "image/jpeg"))])
    assert response.status_code == 200
    payload = response.json()
    assert payload["images"][0]["filename"] == "photo.jpg"
    image_id = payload["images"][0]["image_id"]
    retrieval = client.get(f"/api/inspections/{inspection['inspection_id']}/images/{image_id}")
    assert retrieval.status_code == 200
    assert retrieval.headers["content-type"].startswith("image/jpeg")


def test_valid_png_upload_and_multiple_images():
    inspection = _create_inspection({"po": {"po_id": "PO-2002", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    response = client.post(
        f"/api/inspections/{inspection['inspection_id']}/images",
        files=[
            ("files", ("one.png", _png_bytes(), "image/png")),
            ("files", ("two.png", _png_bytes(), "image/png")),
        ],
    )
    assert response.status_code == 200
    assert len(response.json()["images"]) == 2


def test_invalid_unsupported_file_type_rejected():
    inspection = _create_inspection({"po": {"po_id": "PO-2003", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    response = client.post(f"/api/inspections/{inspection['inspection_id']}/images", files=[("files", ("bad.txt", b"hello", "text/plain"))])
    assert response.status_code == 400


def test_empty_file_rejected():
    inspection = _create_inspection({"po": {"po_id": "PO-2004", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    response = client.post(f"/api/inspections/{inspection['inspection_id']}/images", files=[("files", ("empty.jpg", b"", "image/jpeg"))])
    assert response.status_code == 400


def test_oversized_file_rejected():
    inspection = _create_inspection({"po": {"po_id": "PO-2005", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    huge = b"x" * (11 * 1024 * 1024)
    response = client.post(f"/api/inspections/{inspection['inspection_id']}/images", files=[("files", ("huge.jpg", huge, "image/jpeg"))])
    assert response.status_code == 413


def test_malformed_non_image_with_image_extension_rejected():
    inspection = _create_inspection({"po": {"po_id": "PO-2006", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    response = client.post(f"/api/inspections/{inspection['inspection_id']}/images", files=[("files", ("not_real.png", b"this is not an image", "image/png"))])
    assert response.status_code == 400


def test_missing_inspection_upload_fails():
    response = client.post("/api/inspections/missing-inspection/images", files=[("files", ("upload.png", _png_bytes(), "image/png"))])
    assert response.status_code == 404


def test_image_belongs_to_different_inspection_fails():
    first = _create_inspection({"po": {"po_id": "PO-2007", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    second = _create_inspection({"po": {"po_id": "PO-2008", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    upload = client.post(f"/api/inspections/{first['inspection_id']}/images", files=[("files", ("photo.png", _png_bytes(), "image/png"))])
    image_id = upload.json()["images"][0]["image_id"]
    retrieved = client.get(f"/api/inspections/{second['inspection_id']}/images/{image_id}")
    assert retrieved.status_code == 404


def test_max_image_count_enforced(monkeypatch):
    monkeypatch.setenv("UPLOAD_MAX_IMAGES", "2")
    get_settings.cache_clear()
    inspection = _create_inspection({"po": {"po_id": "PO-2009", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    response = client.post(f"/api/inspections/{inspection['inspection_id']}/images", files=[("files", ("one.png", _png_bytes(), "image/png")), ("files", ("two.png", _png_bytes(), "image/png")), ("files", ("three.png", _png_bytes(), "image/png"))])
    assert response.status_code == 400
    monkeypatch.delenv("UPLOAD_MAX_IMAGES", raising=False)
    get_settings.cache_clear()


def test_missing_image_returns_404():
    inspection = _create_inspection({"po": {"po_id": "PO-2010", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    response = client.get(f"/api/inspections/{inspection['inspection_id']}/images/IMG-DOES-NOT-EXIST")
    assert response.status_code == 404


def test_missing_api_key_for_analysis(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)
    get_settings.cache_clear()
    inspection = _create_inspection({"po": {"po_id": "PO-2011", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    response = client.post(f"/api/inspections/{inspection['inspection_id']}/analyze")
    assert response.status_code == 500
    assert "API key" in response.json()["detail"] or "configured" in response.json()["detail"]


def test_demo_mode_analysis_returns_structured_decision(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    get_settings.cache_clear()
    inspection = _create_inspection({"po": {"po_id": "PO-2012", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    response = client.post(f"/api/inspections/{inspection['inspection_id']}/analyze", params={"scenario": "short_shipment"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] in {"PASS", "EXCEPTION", "UNCERTAIN"}
    assert "checks" in payload
    assert "evidence" in payload
    monkeypatch.delenv("DEMO_MODE", raising=False)
    get_settings.cache_clear()


def test_operator_override_writes_agent_decision_and_reason():
    inspection = _create_inspection({"po": {"po_id": "PO-2013", "sku": "BLUE-BOTTLE-001", "product_name": "Blue Bottle", "expected_quantity": 24, "variant": "Blue", "units_per_carton": 12, "expected_cartons": 2}})
    response = client.post(
        f"/api/inspections/{inspection['inspection_id']}/override",
        json={"decision": "EXCEPTION", "reason": "Visible crushed carton on the right edge."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["override_decision"] == "EXCEPTION"
    assert payload["override_reason"] == "Visible crushed carton on the right edge."
    assert payload["status"] == "completed"

    follow_up = client.get(f"/api/inspections/{inspection['inspection_id']}")
    assert follow_up.status_code == 200
    assert follow_up.json()["override_decision"] == "EXCEPTION"
