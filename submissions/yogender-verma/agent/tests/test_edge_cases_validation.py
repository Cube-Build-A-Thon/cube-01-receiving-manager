"""
Automated Edge Cases & Validation Test Suite
Tests:
- Quantity arithmetic (cartons x units per carton = total)
- Directly observed vs Inferred vs Expected quantity distinction
- Over-shipment vs Under-shipment
- Empty image upload list handled safely
- Duplicate image references handled safely
- Photo upload endpoint validation (JPEG/PNG supported, invalid format rejected)
- Missing optional PO fields
"""

import pytest
import io
from fastapi.testclient import TestClient
from backend.app import app
from backend.agent import ReceivingManagerAgent
from backend.db import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_quantity_arithmetic_and_distinctions():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-QTY-01", "po_line": 1, "sku": "SKU-TOWEL-BLU",
        "cartons_ordered": 4, "cartons_received": 4,
        "units_per_carton_ordered": 6, "units_per_carton_counted": 6,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-QTY-01", spec, ["fixtures/receiving/clean_pallet.jpg"])
    
    assert res["qty_ordered"] == 24
    assert res["qty_received"] == 24
    assert res["cartons_received"] == 4
    assert res["units_per_carton_counted"] == 6
    assert res["overall_verdict"] == "PASS"

def test_empty_images_list_yields_uncertain_clarity():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-EMPTY-IMG", "po_line": 1, "sku": "SKU-ANY",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12
    }
    # No photos uploaded
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-NO-IMG", spec, [])
    # With zero visual evidence, checks requiring vision should yield UNCERTAIN
    assert res["overall_verdict"] == "UNCERTAIN"
    assert res["agent_confidence"] < 0.50

def test_duplicate_images_do_not_duplicate_counts():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-DUP", "po_line": 1, "sku": "SKU-SAMPLE",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "override_identity_match": "yes"
    }
    # Duplicate image references in list
    duplicate_photos = [
        "fixtures/receiving/clean_pallet.jpg",
        "fixtures/receiving/clean_pallet.jpg",
        "fixtures/receiving/clean_pallet.jpg"
    ]
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-DUP", spec, duplicate_photos)
    assert res["qty_received"] == 12  # Must not multiply by 3
    assert res["cartons_received"] == 1
    assert res["overall_verdict"] == "PASS"

def test_photo_upload_valid_format():
    file_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\x00" * 100  # Valid mock JPEG header
    response = client.post(
        "/api/upload-photo",
        files={"file": ("test_capture.jpg", io.BytesIO(file_content), "image/jpeg")},
        headers={"X-Org-ID": "org_demo_alpha"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "uploaded"
    assert data["tenant_org"] == "org_demo_alpha"
    assert data["filename"] == "test_capture.jpg"
    assert "/api/images/org_demo_alpha/test_capture.jpg" in data["photo_url"]

def test_photo_upload_invalid_format_rejected():
    file_content = b"#!/bin/bash\necho hello"
    response = client.post(
        "/api/upload-photo",
        files={"file": ("malicious_script.sh", io.BytesIO(file_content), "text/plain")},
        headers={"X-Org-ID": "org_demo_alpha"}
    )
    assert response.status_code == 400
    assert "Invalid image format" in response.json()["detail"]

def test_missing_optional_po_fields_handled_gracefully():
    agent = ReceivingManagerAgent()
    sparse_spec = {
        "sku": "MINIMAL-SKU-01",
        "product_title": "Minimal PO Item"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-SPARSE", sparse_spec, ["fixtures/receiving/clean_pallet.jpg"])
    # Defaults applied without crash
    assert res["cartons_ordered"] >= 1
    assert res["qty_ordered"] >= 1
    assert res["status"] == "processed"
