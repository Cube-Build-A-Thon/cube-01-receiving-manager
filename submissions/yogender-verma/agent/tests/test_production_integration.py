"""
Production Integration Test Suite (Priorities 1 to 14)
Validates all 20 explicit requirements:
1. Correct shipment
2. Short shipment
3. Wrong SKU
4. Wrong variant
5. Crushed carton
6. Water damage
7. Torn packaging
8. Missing components
9. Ambiguous / UNCERTAIN
10. Gemini/API failure -> PENDING_REVIEW
11. Retry after failure
12. Original failure remains in audit history
13. shipment_id persistence
14. cross-pod contract contains shipment_id
15. cross-pod check-key names
16. live uncertain-rate endpoint
17. tenant isolation for new records, attempts, and metrics
18. multiple-photo inspection
19. additional-evidence reinspection
20. REAL_AI does not silently become DEMO
"""

import pytest
import json
from fastapi.testclient import TestClient
from backend.app import app
from backend.agent import ReceivingManagerAgent
from backend.contract import generate_evidence_contract, RECEIVING_EVIDENCE_SCHEMA_V1
from backend.db import (
    init_db,
    get_record_by_id_scoped,
    get_attempts_by_record,
    record_inspection_attempt,
    get_db_connection
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inspection_attempts WHERE record_id LIKE 'RCV-INT-%'")
    cursor.execute("DELETE FROM receiving_records WHERE record_id LIKE 'RCV-INT-%'")
    conn.commit()
    conn.close()

# 1. Correct shipment
def test_1_correct_shipment():
    payload = {
        "unit_id": "UNIT-INT-01",
        "shipment_id": "SH-1001-A",
        "po_number": "PO-1001",
        "po_line": 1,
        "supplier": "Apex Hydro",
        "sku": "BLUE-BOTTLE-001",
        "asin": "B08N5KWB9H",
        "product_title": "Blue Stainless Steel Bottle",
        "spec_colour": "Blue",
        "spec_variant": "Standard",
        "spec_components": "bottle; lid",
        "cartons_ordered": 2,
        "cartons_received": 2,
        "units_per_carton_ordered": 12,
        "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "override_identity_match": "yes"
    }
    res = client.post("/api/inspect", json=payload, headers={"X-Org-ID": "org_demo_alpha"})
    assert res.status_code == 200
    data = res.json()
    assert data["overall_verdict"] == "PASS"
    assert data["shipment_id"] == "SH-1001-A"

# 2. Short shipment
def test_2_short_shipment():
    payload = {
        "unit_id": "UNIT-INT-02",
        "shipment_id": "SH-1002-B",
        "po_number": "PO-1002",
        "po_line": 1,
        "supplier": "Apex Hydro",
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 2,
        "cartons_received": 2,
        "units_per_carton_ordered": 12,
        "units_per_carton_counted": 10,  # 20 received vs 24 ordered
        "photo_refs": ["fixtures/receiving/short_shipment.jpg"],
        "override_identity_match": "yes"
    }
    res = client.post("/api/inspect", json=payload, headers={"X-Org-ID": "org_demo_alpha"})
    assert res.status_code == 200
    data = res.json()
    assert data["overall_verdict"] == "FAIL"
    assert data["qty_received"] < data["qty_ordered"]

# 3. Wrong SKU
def test_3_wrong_sku():
    payload = {
        "unit_id": "UNIT-INT-03",
        "shipment_id": "SH-1003-C",
        "po_number": "PO-1003",
        "po_line": 1,
        "supplier": "Apex Hydro",
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 2,
        "cartons_received": 2,
        "units_per_carton_ordered": 12,
        "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/wrong_sku.jpg"],
        "override_identity_match": "no"
    }
    res = client.post("/api/inspect", json=payload, headers={"X-Org-ID": "org_demo_alpha"})
    assert res.status_code == 200
    data = res.json()
    assert data["overall_verdict"] == "FAIL"
    assert data["identity_match"] == "no"

# 4. Wrong variant
def test_4_wrong_variant():
    payload = {
        "unit_id": "UNIT-INT-04",
        "po_number": "PO-1004",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 2,
        "cartons_received": 2,
        "units_per_carton_ordered": 12,
        "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "override_identity_match": "yes",
        "override_quality_flags": ["wrong_variant"]
    }
    res = client.post("/api/inspect", json=payload, headers={"X-Org-ID": "org_demo_alpha"})
    assert res.status_code == 200
    data = res.json()
    assert data["overall_verdict"] == "FAIL"
    assert "wrong_variant" in data["quality_flags"]

# 5. Crushed carton
def test_5_crushed_carton():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1005", "po_line": 1, "sku": "BLUE-BOTTLE-001",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-INT-05", spec, ["fixtures/pallet_crushing.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert res["carton_damage"] == "crushing"

# 6. Water damage
def test_6_water_damage():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1006", "po_line": 1, "sku": "BLUE-BOTTLE-001",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-INT-06", spec, ["fixtures/carton_water_soaked.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert res["carton_damage"] == "water"

# 7. Torn packaging
def test_7_torn_packaging():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1007", "po_line": 1, "sku": "BLUE-BOTTLE-001",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-INT-07", spec, ["fixtures/packaging_tears.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert res["carton_damage"] == "tears"

# 8. Missing components
def test_8_missing_components():
    payload = {
        "unit_id": "UNIT-INT-08",
        "po_number": "PO-1008",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 2,
        "cartons_received": 2,
        "units_per_carton_ordered": 12,
        "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "override_identity_match": "yes",
        "override_quality_flags": ["missing_components"]
    }
    res = client.post("/api/inspect", json=payload, headers={"X-Org-ID": "org_demo_alpha"})
    assert res.status_code == 200
    data = res.json()
    assert data["overall_verdict"] == "FAIL"
    assert "missing_components" in data["quality_flags"]

# 9. Ambiguous / UNCERTAIN
def test_9_ambiguous_uncertain():
    payload = {
        "unit_id": "UNIT-INT-09",
        "po_number": "PO-1009",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 2,
        "cartons_received": 2,
        "units_per_carton_ordered": 12,
        "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "override_identity_match": "uncertain"
    }
    res = client.post("/api/inspect", json=payload, headers={"X-Org-ID": "org_demo_alpha"})
    assert res.status_code == 200
    data = res.json()
    assert data["overall_verdict"] == "UNCERTAIN"
    assert data["overall_decision"] == "UNCERTAIN"

# 10. Gemini/API failure -> PENDING_REVIEW
def test_10_gemini_api_failure_pending_review():
    payload = {
        "unit_id": "UNIT-INT-10",
        "po_number": "PO-1010",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 2,
        "cartons_received": 2,
        "units_per_carton_ordered": 12,
        "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "simulate_fail_open": True
    }
    res = client.post("/api/inspect", json=payload, headers={"X-Org-ID": "org_demo_alpha"})
    assert res.status_code == 200
    data = res.json()
    assert data["overall_verdict"] == "PENDING_REVIEW"
    assert data["status"] == "pending_review"

# 11 & 12. Retry after failure and original failure remains in audit history
def test_11_and_12_retry_preserves_history():
    # Attempt 1: Fail open
    p1 = {
        "unit_id": "UNIT-INT-11",
        "shipment_id": "SH-AUDIT-11",
        "po_number": "PO-1011",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 2,
        "cartons_received": 2,
        "units_per_carton_ordered": 12,
        "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "simulate_fail_open": True
    }
    res1 = client.post("/api/inspect", json=p1, headers={"X-Org-ID": "org_demo_alpha"})
    assert res1.status_code == 200
    rec_id = res1.json()["record_id"]

    # Verify attempt 1 was recorded
    attempts_1 = get_attempts_by_record(rec_id, "org_demo_alpha")
    assert len(attempts_1) == 1
    assert attempts_1[0]["overall_verdict"] == "PENDING_REVIEW"
    assert attempts_1[0]["attempt_number"] == 1

    # Attempt 2: Retry
    res2 = client.post(f"/api/records/{rec_id}/retry", headers={"X-Org-ID": "org_demo_alpha"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["overall_verdict"] == "PASS"

    # Verify both Attempt 1 and Attempt 2 exist in audit history
    attempts_2 = get_attempts_by_record(rec_id, "org_demo_alpha")
    assert len(attempts_2) == 2
    assert attempts_2[0]["attempt_number"] == 1
    assert attempts_2[0]["overall_verdict"] == "PENDING_REVIEW"
    assert attempts_2[1]["attempt_number"] == 2
    assert attempts_2[1]["overall_verdict"] == "PASS"

# 13. shipment_id persistence (including null handling)
def test_13_shipment_id_persistence():
    # Test with valid shipment_id
    p1 = {
        "unit_id": "UNIT-INT-13A",
        "shipment_id": "SHIP-XYZ-999",
        "po_number": "PO-1013",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "override_identity_match": "yes"
    }
    res1 = client.post("/api/inspect", json=p1, headers={"X-Org-ID": "org_demo_alpha"})
    assert res1.status_code == 200
    r1 = res1.json()
    assert r1["shipment_id"] == "SHIP-XYZ-999"

    # Query back from DB
    db_rec1 = get_record_by_id_scoped(r1["record_id"], "org_demo_alpha")
    assert db_rec1["shipment_id"] == "SHIP-XYZ-999"

    # Test with null shipment_id (backwards compatibility)
    p2 = {
        "unit_id": "UNIT-INT-13B",
        "shipment_id": None,
        "po_number": "PO-1013B",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "override_identity_match": "yes"
    }
    res2 = client.post("/api/inspect", json=p2, headers={"X-Org-ID": "org_demo_alpha"})
    assert res2.status_code == 200
    r2 = res2.json()
    assert r2["shipment_id"] is None
    db_rec2 = get_record_by_id_scoped(r2["record_id"], "org_demo_alpha")
    assert db_rec2["shipment_id"] is None

# 14. cross-pod contract contains shipment_id
def test_14_cross_pod_contract_contains_shipment_id():
    p = {
        "unit_id": "UNIT-INT-14",
        "shipment_id": "SHIP-CONTRACT-44",
        "po_number": "PO-1014",
        "po_line": 2,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "override_identity_match": "yes"
    }
    res = client.post("/api/inspect", json=p, headers={"X-Org-ID": "org_demo_alpha"})
    assert res.status_code == 200
    record_id = res.json()["record_id"]

    contract_res = client.get(f"/api/contract/{record_id}", headers={"X-Org-ID": "org_demo_alpha"})
    assert contract_res.status_code == 200
    contract = contract_res.json()
    assert "subject" in contract
    assert contract["subject"]["shipment_id"] == "SHIP-CONTRACT-44"
    assert contract["subject"]["order_id"] == "PO-1014"
    assert contract["subject"]["po_line_id"] == "2"

# 15. cross-pod check-key names
def test_15_cross_pod_check_key_names():
    p = {
        "unit_id": "UNIT-INT-15",
        "shipment_id": "SH-KEYS-15",
        "po_number": "PO-1015",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "override_identity_match": "yes"
    }
    res = client.post("/api/inspect", json=p, headers={"X-Org-ID": "org_demo_alpha"})
    assert res.status_code == 200
    record_id = res.json()["record_id"]

    contract_res = client.get(f"/api/contract/{record_id}", headers={"X-Org-ID": "org_demo_alpha"})
    assert contract_res.status_code == 200
    contract = contract_res.json()

    expected_keys = {
        "identity_matches_po",
        "quantity_matches_po",
        "carton_undamaged",
        "unit_undamaged",
        "variant_correct"
    }
    checks = contract.get("checks", [])
    if isinstance(checks, list):
        found_keys = {c.get("check_key") for c in checks}
    else:
        found_keys = set(checks.keys())
    for k in expected_keys:
        assert k in found_keys, f"Expected cross-pod check key '{k}' missing from contract checks: {found_keys}"

# 16. live uncertain-rate endpoint
def test_16_live_uncertain_rate_endpoint():
    tenant = "org_metrics_test"
    # Seed 1 PASS, 1 FAIL, 1 UNCERTAIN, 1 PENDING_REVIEW
    inspections = [
        {"override_identity_match": "yes"},                           # PASS
        {"units_per_carton_counted": 5, "override_identity_match": "yes"}, # FAIL
        {"override_identity_match": "uncertain"},                     # UNCERTAIN
        {"simulate_fail_open": True}                                   # PENDING_REVIEW
    ]
    for idx, extra in enumerate(inspections):
        body = {
            "unit_id": f"UNIT-METRIC-{idx}",
            "po_number": "PO-METRIC",
            "po_line": 1,
            "sku": "BLUE-BOTTLE-001",
            "product_title": "Blue Stainless Steel Bottle",
            "cartons_ordered": 1, "cartons_received": 1,
            "units_per_carton_ordered": 10, "units_per_carton_counted": 10,
            "photo_refs": ["fixtures/receiving/clean_pallet.jpg"]
        }
        body.update(extra)
        res = client.post("/api/inspect", json=body, headers={"X-Org-ID": tenant})
        assert res.status_code == 200

    res = client.get("/api/metrics/live", headers={"X-Org-ID": tenant})
    assert res.status_code == 200
    metrics = res.json()
    assert metrics["total_inspections"] == 4
    assert metrics["pass_count"] == 1
    assert metrics["fail_count"] == 1
    assert metrics["uncertain_count"] == 1
    assert metrics["pending_review_count"] == 1
    assert metrics["completed_inspections"] == 3  # Excludes PENDING_REVIEW
    # 1 UNCERTAIN / 3 completed = ~0.3333
    assert abs(metrics["uncertain_rate"] - 0.3333) < 0.01

# 17. tenant isolation for new records, attempts, and metrics
def test_17_tenant_isolation_new_records():
    # Insert for org_tenant_a
    p = {
        "unit_id": "UNIT-SECRET-A",
        "shipment_id": "SH-SECRET-A",
        "po_number": "PO-SECRET-A",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 10, "units_per_carton_counted": 10,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "override_identity_match": "yes"
    }
    res_a = client.post("/api/inspect", json=p, headers={"X-Org-ID": "org_tenant_a"})
    assert res_a.status_code == 200
    record_id = res_a.json()["record_id"]

    # Attempt to read record from org_tenant_b -> 404
    res_b = client.get(f"/api/records/{record_id}", headers={"X-Org-ID": "org_tenant_b"})
    assert res_b.status_code == 404

    # Attempt to read contract from org_tenant_b -> 404
    res_contract_b = client.get(f"/api/contract/{record_id}", headers={"X-Org-ID": "org_tenant_b"})
    assert res_contract_b.status_code == 404

    # Attempt to read attempts from org_tenant_b -> 404
    res_attempts_b = client.get(f"/api/records/{record_id}/attempts", headers={"X-Org-ID": "org_tenant_b"})
    assert res_attempts_b.status_code == 404

    # Attempt to reinspect from org_tenant_b -> 404
    res_reinspect_b = client.post(
        f"/api/records/{record_id}/reinspect",
        json={"photo_refs": ["fixtures/receiving/clean_pallet.jpg"]},
        headers={"X-Org-ID": "org_tenant_b"}
    )
    assert res_reinspect_b.status_code == 404

# 18. multiple-photo inspection
def test_18_multiple_photo_inspection():
    photos = [
        "fixtures/receiving/clean_pallet.jpg",
        "fixtures/receiving/UNIT-0101_carton_clean.jpg"
    ]
    p = {
        "unit_id": "UNIT-INT-18",
        "po_number": "PO-1018",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "photo_refs": photos,
        "override_identity_match": "yes"
    }
    res = client.post("/api/inspect", json=p, headers={"X-Org-ID": "org_demo_alpha"})
    assert res.status_code == 200
    data = res.json()
    assert "clean_pallet.jpg" in data["photo_refs"]
    assert "carton_clean.jpg" in data["photo_refs"]
    assert ";" in data["photo_refs"]

# 19. additional-evidence reinspection
def test_19_additional_evidence_reinspection():
    # Step 1: Initial inspection returns UNCERTAIN
    p = {
        "unit_id": "UNIT-INT-19",
        "shipment_id": "SH-OCCLUDED-19",
        "po_number": "PO-1019",
        "po_line": 1,
        "sku": "BLUE-BOTTLE-001",
        "product_title": "Blue Stainless Steel Bottle",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "photo_refs": ["fixtures/receiving/UNIT-0107_carton_ambiguous.jpg"],
        "override_identity_match": "uncertain"
    }
    res = client.post("/api/inspect", json=p, headers={"X-Org-ID": "org_demo_alpha"})
    assert res.status_code == 200
    rec_id = res.json()["record_id"]
    assert res.json()["overall_verdict"] == "UNCERTAIN"

    # Step 2: Operator submits additional photo evidence & reinspects
    reinspect_body = {
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "notes": "Cleared shrink-wrap and provided high resolution pallet view"
    }
    reinspect_res = client.post(
        f"/api/records/{rec_id}/reinspect",
        json=reinspect_body,
        headers={"X-Org-ID": "org_demo_alpha"}
    )
    assert reinspect_res.status_code == 200
    reinspect_data = reinspect_res.json()
    assert reinspect_data["reinspect_success"] is True

    # Step 3: Check attempts history
    attempts = reinspect_data["attempts"]
    assert len(attempts) >= 2
    # Attempt 1 must be preserved as UNCERTAIN
    assert attempts[0]["overall_verdict"] == "UNCERTAIN"
    assert attempts[0]["attempt_number"] == 1
    # Attempt 2 must be recorded
    assert attempts[1]["attempt_number"] == 2

# 20. REAL_AI does not silently become DEMO
def test_20_real_ai_does_not_silently_become_demo():
    agent = ReceivingManagerAgent()
    agent.is_real_ai = True
    spec = {
        "po_number": "PO-1020", "po_line": 1, "sku": "BLUE-BOTTLE-001",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12
    }
    # When simulated fail open is triggered or API is offline
    res = agent.run_batch_receiving_inspection(
        org_id="org_demo_alpha",
        unit_id="UNIT-INT-20",
        po_line_spec=spec,
        captured_images=["fixtures/receiving/clean_pallet.jpg"],
        simling_failure=True
    )
    # Must NOT silently switch to DEMO_MODE_SYNTHETIC
    assert res["is_real_ai"] is True
    assert res["execution_mode"] != "DEMO_MODE_SYNTHETIC"
    assert res["execution_mode"] == "REAL_AI_MULTIMODAL"
    assert res["overall_verdict"] == "PENDING_REVIEW"
