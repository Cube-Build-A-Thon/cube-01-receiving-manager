"""
Test Suite: Authoritative Evidence Contract v1.1 Compliance & /v1 API Surface
Covers all 30 contract verification requirements.
"""

import pytest
import uuid
import json
from fastapi.testclient import TestClient
from backend.app import app
from backend.contract import generate_evidence_contract, to_contract_uuid, compute_content_hash

client = TestClient(app)

TENANT_ALPHA = "org_test_v1_alpha"
TENANT_BRAVO = "org_test_v1_bravo"


def test_01_schema_version_is_1_1():
    p = {
        "unit_id": "UNIT-V1-01",
        "shipment_id": "SH-V1-01",
        "po_number": "PO-V1-01",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"]
    }
    res = client.post("/api/inspect", json=p, headers={"X-Org-ID": TENANT_ALPHA})
    assert res.status_code == 200
    rec_id = res.json()["record_id"]

    contract_res = client.get(f"/v1/records/{rec_id}", headers={"X-Org-ID": TENANT_ALPHA})
    assert contract_res.status_code == 200
    contract = contract_res.json()

    # 1. schema_version == "1.1"
    assert contract["schema_version"] == "1.1"
    # 2. organization_id exists
    assert "organization_id" in contract
    assert contract["organization_id"] == TENANT_ALPHA
    # 3. client_id exists and is null
    assert "client_id" in contract
    assert contract["client_id"] is None
    # 4. agent == "receiving"
    assert contract["agent"] == "receiving"


def test_02_record_id_is_valid_deterministic_uuid():
    internal_id = "RCV-V1-SAMPLE-99"
    u1 = to_contract_uuid(internal_id)
    u2 = to_contract_uuid(internal_id)
    assert u1 == u2
    # Verify valid RFC 4122 UUID
    parsed = uuid.UUID(u1)
    assert str(parsed) == u1


def test_03_subject_flat_structure_and_shipment_id():
    p = {
        "unit_id": "UNIT-V1-03",
        "shipment_id": "SHIP-ALPHA-777",
        "po_number": "PO-7770",
        "po_line": 3,
        "sku": "BOTTLE-GREEN-02",
        "asin": "B07XYZ999",
        "cartons_ordered": 3, "cartons_received": 3,
        "units_per_carton_ordered": 10, "units_per_carton_counted": 10,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"]
    }
    res = client.post("/api/inspect", json=p, headers={"X-Org-ID": TENANT_ALPHA})
    assert res.status_code == 200
    rec_id = res.json()["record_id"]

    contract = client.get(f"/v1/records/{rec_id}", headers={"X-Org-ID": TENANT_ALPHA}).json()
    subj = contract["subject"]

    assert subj["type"] == "unit"
    assert subj["shipment_id"] == "SHIP-ALPHA-777"
    assert subj["sku"] == "BOTTLE-GREEN-02"
    assert subj["asin"] == "B07XYZ999"
    assert subj["order_id"] == "PO-7770"
    assert subj["po_line_id"] == "3"
    assert subj["quantity_expected"] == 30
    assert subj["quantity_observed"] == 30


def test_04_images_array_and_real_sha256():
    p = {
        "unit_id": "UNIT-V1-04",
        "po_number": "PO-V1-04",
        "sku": "BLUE-BOTTLE-001",
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"]
    }
    res = client.post("/api/inspect", json=p, headers={"X-Org-ID": TENANT_ALPHA})
    rec_id = res.json()["record_id"]

    contract = client.get(f"/v1/records/{rec_id}", headers={"X-Org-ID": TENANT_ALPHA}).json()
    images = contract.get("images")
    assert isinstance(images, list)
    assert len(images) >= 1

    img = images[0]
    assert "key" in img
    assert "sha256" in img
    assert len(img["sha256"]) == 64  # valid hex SHA-256
    assert "bytes" in img
    assert isinstance(img["bytes"], int)
    assert img["bytes"] > 0
    assert "taken_at" in img


def test_05_checks_is_array_with_five_keys_and_lowercase_verdicts():
    p = {
        "unit_id": "UNIT-V1-05",
        "po_number": "PO-V1-05",
        "sku": "BLUE-BOTTLE-001",
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"]
    }
    res = client.post("/api/inspect", json=p, headers={"X-Org-ID": TENANT_ALPHA})
    rec_id = res.json()["record_id"]

    contract = client.get(f"/v1/records/{rec_id}", headers={"X-Org-ID": TENANT_ALPHA}).json()
    checks = contract.get("checks")
    assert isinstance(checks, list)
    assert len(checks) == 5

    expected_keys = [
        "identity_matches_po",
        "quantity_matches_po",
        "carton_undamaged",
        "unit_undamaged",
        "variant_correct"
    ]
    found_keys = [c["check_key"] for c in checks]
    assert found_keys == expected_keys

    valid_verdicts = {"pass", "fail", "uncertain"}
    for c in checks:
        assert c["verdict"] in valid_verdicts
        # Must be strictly lowercase
        assert c["verdict"] == c["verdict"].lower()
        assert 0.0 <= c["confidence"] <= 1.0
        assert isinstance(c["detail"], dict)
        assert isinstance(c["model_version"], str) and len(c["model_version"]) > 0
        assert isinstance(c["latency_ms"], int) and c["latency_ms"] >= 0


def test_06_outcome_object_structure():
    p = {
        "unit_id": "UNIT-V1-06",
        "po_number": "PO-V1-06",
        "sku": "BLUE-BOTTLE-001",
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"]
    }
    res = client.post("/api/inspect", json=p, headers={"X-Org-ID": TENANT_ALPHA})
    rec_id = res.json()["record_id"]

    contract = client.get(f"/v1/records/{rec_id}", headers={"X-Org-ID": TENANT_ALPHA}).json()
    outcome = contract.get("outcome")
    assert isinstance(outcome, dict)
    assert "decision" in outcome
    assert outcome["decided_by"] in ["agent", "operator"]
    assert "decided_at" in outcome


def test_07_overrides_array_structure():
    p = {
        "unit_id": "UNIT-V1-07",
        "po_number": "PO-V1-07",
        "sku": "BLUE-BOTTLE-001",
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"]
    }
    res = client.post("/api/inspect", json=p, headers={"X-Org-ID": TENANT_ALPHA})
    rec_id = res.json()["record_id"]

    # Perform an override with mandatory reason
    ov_res = client.post(
        f"/api/records/{rec_id}/override",
        json={
            "operator_id": "op_test_lead",
            "override_reason": "Verified package label matches physical manifest",
            "identity_match": "yes"
        },
        headers={"X-Org-ID": TENANT_ALPHA}
    )
    assert ov_res.status_code == 200

    contract = client.get(f"/v1/records/{rec_id}", headers={"X-Org-ID": TENANT_ALPHA}).json()
    assert contract["outcome"]["decided_by"] == "operator"

    overrides = contract.get("overrides")
    assert isinstance(overrides, list)
    assert len(overrides) >= 1
    ov = overrides[0]
    assert "check_key" in ov
    assert ov["from_verdict"] in ["pass", "fail", "uncertain"]
    assert ov["to_verdict"] in ["pass", "fail", "uncertain"]
    assert ov["reason"] == "Verified package label matches physical manifest"
    assert ov["by"] == "op_test_lead"
    assert "at" in ov


def test_08_status_and_pending_mapping():
    # Normal completed inspection -> status == "complete"
    p1 = {
        "unit_id": "UNIT-V1-08A",
        "po_number": "PO-V1-08A",
        "sku": "BLUE-BOTTLE-001",
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"]
    }
    r1 = client.post("/api/inspect", json=p1, headers={"X-Org-ID": TENANT_ALPHA}).json()
    c1 = client.get(f"/v1/records/{r1['record_id']}", headers={"X-Org-ID": TENANT_ALPHA}).json()
    assert c1["status"] == "complete"

    # Fail-open simulated timeout -> status == "pending"
    p2 = {
        "unit_id": "UNIT-V1-08B",
        "po_number": "PO-V1-08B",
        "sku": "BLUE-BOTTLE-001",
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "simulate_fail_open": True
    }
    r2 = client.post("/api/inspect", json=p2, headers={"X-Org-ID": TENANT_ALPHA}).json()
    c2 = client.get(f"/v1/records/{r2['record_id']}", headers={"X-Org-ID": TENANT_ALPHA}).json()
    assert c2["status"] == "pending"
    assert c2["outcome"]["decision"] == "pending"


def test_09_deterministic_content_hash():
    p = {
        "unit_id": "UNIT-V1-09",
        "po_number": "PO-V1-09",
        "sku": "BLUE-BOTTLE-001",
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"]
    }
    r = client.post("/api/inspect", json=p, headers={"X-Org-ID": TENANT_ALPHA}).json()
    rec_id = r["record_id"]

    c1 = client.get(f"/v1/records/{rec_id}", headers={"X-Org-ID": TENANT_ALPHA}).json()
    c2 = client.get(f"/v1/records/{rec_id}", headers={"X-Org-ID": TENANT_ALPHA}).json()

    assert "content_hash" in c1
    assert len(c1["content_hash"]) == 64
    assert c1["content_hash"] == c2["content_hash"]


def test_10_v1_captures_and_complete_lifecycle():
    # 1. POST /v1/captures
    cap_res = client.post(
        "/v1/captures",
        json={
            "unit_id": "UNIT-V1-CAP-10",
            "shipment_id": "SH-CAP-10",
            "po_number": "PO-CAP-10",
            "expected_images_count": 2
        },
        headers={"X-Org-ID": TENANT_ALPHA}
    )
    assert cap_res.status_code == 200
    cap_data = cap_res.json()
    assert "capture_id" in cap_data
    assert "upload_urls" in cap_data
    assert len(cap_data["upload_urls"]) == 2
    capture_id = cap_data["capture_id"]

    # 2. POST /v1/captures/{id}/complete
    comp_res = client.post(
        f"/v1/captures/{capture_id}/complete",
        json={"photo_refs": ["fixtures/receiving/clean_pallet.jpg"]},
        headers={"X-Org-ID": TENANT_ALPHA}
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert "record_id" in comp_data
    assert comp_data["status"] == "complete"
    record_uuid = comp_data["record_id"]

    # 3. GET /v1/records/{record_uuid}
    rec_res = client.get(f"/v1/records/{record_uuid}", headers={"X-Org-ID": TENANT_ALPHA})
    assert rec_res.status_code == 200
    record = rec_res.json()
    assert record["record_id"] == record_uuid
    assert record["schema_version"] == "1.1"
    assert record["subject"]["shipment_id"] == "SH-CAP-10"


def test_11_v1_list_records_and_filters():
    # Query with agent=receiving
    res = client.get("/v1/records?agent=receiving&limit=5", headers={"X-Org-ID": TENANT_ALPHA})
    assert res.status_code == 200
    data = res.json()
    assert "records" in data
    assert isinstance(data["records"], list)
    for r in data["records"]:
        assert r["agent"] == "receiving"
        assert r["schema_version"] == "1.1"

    # Query with agent=returns (should return empty list)
    res_other = client.get("/v1/records?agent=returns", headers={"X-Org-ID": TENANT_ALPHA})
    assert res_other.status_code == 200
    assert res_other.json()["records"] == []

    # Query with since filter
    res_since = client.get("/v1/records?since=2020-01-01T00:00:00Z&limit=10", headers={"X-Org-ID": TENANT_ALPHA})
    assert res_since.status_code == 200
    assert len(res_since.json()["records"]) >= 1


def test_12_v1_endpoints_tenant_isolation():
    # Create record in TENANT_ALPHA
    p = {
        "unit_id": "UNIT-V1-SECRET-12",
        "po_number": "PO-V1-SECRET",
        "sku": "BLUE-BOTTLE-001"
    }
    res = client.post("/api/inspect", json=p, headers={"X-Org-ID": TENANT_ALPHA})
    rec_id = res.json()["record_id"]

    # Attempt to read from TENANT_BRAVO -> 404
    leak_single = client.get(f"/v1/records/{rec_id}", headers={"X-Org-ID": TENANT_BRAVO})
    assert leak_single.status_code == 404

    # List records in TENANT_BRAVO should NOT contain TENANT_ALPHA's record
    list_bravo = client.get("/v1/records", headers={"X-Org-ID": TENANT_BRAVO}).json()
    bravo_order_ids = [r["subject"]["order_id"] for r in list_bravo["records"]]
    assert "PO-V1-SECRET" not in bravo_order_ids
