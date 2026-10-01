"""
Automated Decision System & Evidence Traceability Test Suite
Tests:
- Deterministic decision aggregation (FAIL -> EXCEPTION, UNCERTAIN -> UNCERTAIN, PASS -> PASS)
- Evidence contract schema validation
- Traceability: Expected vs Observed vs Checked vs Why
- Operator override retains original AI verdict and logs audit trail
"""

import pytest
import json
from fastapi.testclient import TestClient
from backend.app import app
from backend.agent import ReceivingManagerAgent
from backend.contract import generate_evidence_contract, RECEIVING_EVIDENCE_SCHEMA_V1
from backend.db import init_db, get_records_by_org, save_operator_override, get_db_connection

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_aggregation_rule_fail_trumps_uncertain():
    """If one check is FAIL and another is UNCERTAIN, overall must be EXCEPTION (FAIL)."""
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-AGG-01", "po_line": 1, "sku": "BLUE-BOTTLE-001",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 10, # Short shipment (FAIL)
        "override_identity_match": "uncertain" # SKU uncertain
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-AGG-01", spec, ["fixtures/receiving/clean_pallet.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert res["overall_decision"] == "EXCEPTION"

def test_aggregation_rule_all_pass_yields_pass():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-AGG-02", "po_line": 1, "sku": "BLUE-BOTTLE-001",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-AGG-02", spec, ["fixtures/receiving/clean_pallet.jpg"])
    assert res["overall_verdict"] == "PASS"
    assert res["overall_decision"] == "PASS"

def test_evidence_traceability_structure():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-EVID-01", "po_line": 1, "sku": "CANDLE-3PK",
        "product_title": "Soy Candle Set",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 6, "units_per_carton_counted": 6,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-EVID-01", spec, ["fixtures/receiving/pallet_crushing.jpg"])
    evidence = json.loads(res["evidence_data"])

    # WHAT WAS EXPECTED?
    assert "what_expected" in evidence
    assert evidence["what_expected"]["sku"] == "CANDLE-3PK"
    assert evidence["what_expected"]["qty_ordered"] == 6

    # WHAT WAS RECEIVED?
    assert "what_received" in evidence
    assert evidence["what_received"]["total_qty_received"] == 6

    # WHAT WAS CHECKED & WHAT WAS OBSERVED?
    assert "individual_checks" in evidence
    check_names = [c["check_name"] for c in evidence["individual_checks"]]
    assert "Product/SKU Identity" in check_names
    assert "Quantity Verification" in check_names
    assert "Carton Physical Integrity" in check_names

    # WHAT WAS THE VERDICT?
    assert evidence["overall_verdict"] == "FAIL"
    assert evidence["overall_decision"] == "EXCEPTION"

    # WHY?
    assert len(evidence["decision_rationale"]) > 0
    assert "Carton Physical Integrity" in evidence["decision_rationale"]

def test_evidence_contract_generation_matches_schema():
    records = get_records_by_org("org_demo_alpha")
    sample_rec = records[0]
    
    contract = generate_evidence_contract(sample_rec)
    assert contract["schema_version"] == "1.1"
    assert contract["agent"] == "receiving"
    assert "subject" in contract
    assert "images" in contract
    assert "checks" in contract
    assert "outcome" in contract
    assert "overrides" in contract
    assert "status" in contract
    assert "content_hash" in contract

def test_operator_override_retains_history():
    records = get_records_by_org("org_demo_alpha")
    target_rec = records[0]
    target_id = target_rec["record_id"]
    orig_verdict = target_rec["overall_verdict"]

    override_resp = client.post(
        f"/api/records/{target_id}/override",
        json={
            "operator_id": "op_dock_chief",
            "override_reason": "Superficial smudge on outer protective plastic, actual carton pristine.",
            "identity_match": "yes",
            "carton_damage": "none",
            "unit_damage": "none",
            "quality_flags": ""
        },
        headers={"X-Org-ID": "org_demo_alpha"}
    )
    assert override_resp.status_code == 200
    assert override_resp.json()["override_recorded"] is True

    # Retrieve record detail via API and verify audit history is attached
    get_resp = client.get(f"/api/records/{target_id}", headers={"X-Org-ID": "org_demo_alpha"})
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert "audit_overrides" in detail
    assert len(detail["audit_overrides"]) >= 1
    latest_override = detail["audit_overrides"][0]
    assert latest_override["operator_id"] == "op_dock_chief"
    assert latest_override["original_overall_verdict"] == orig_verdict
    assert "Superficial smudge" in latest_override["override_reason"]
