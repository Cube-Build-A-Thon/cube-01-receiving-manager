"""
Automated Fail-Open & Retry Test Suite
Verifies Engineering Rule 3:
1. Model errors or timeouts still save the capture and mark status as PENDING / PENDING_REVIEW.
2. Nothing blocks the receiving operator at the warehouse dock.
3. Retry endpoint successfully re-processes pending records when connectivity recovers.
4. Malformed data does not crash the agent or fabricate fake inspection results.
"""

import pytest
import json
from fastapi.testclient import TestClient
from backend.app import app
from backend.agent import ReceivingManagerAgent
from backend.db import init_db, get_record_by_id_scoped

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_model_timeout_fail_open_behavior():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-FAIL-OPEN", "po_line": 1, "supplier": "Supplier Resilient",
        "sku": "FAILOPEN-01", "asin": "B0FAILOPEN", "product_title": "Fail Open Test Item",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 10, "units_per_carton_counted": 10
    }
    # Simulate network latency timeout / service drop
    result = agent.run_batch_receiving_inspection(
        org_id="org_demo_alpha",
        unit_id="UNIT-FAIL-OPEN-01",
        po_line_spec=spec,
        captured_images=["fixtures/receiving/clean_pallet.jpg"],
        simling_failure=True
    )

    assert result["overall_verdict"] == "PENDING_REVIEW"
    assert result["overall_decision"] == "PENDING"
    assert result["status"] == "pending_review"
    assert result["agent_confidence"] == 0.0

    # Ensure dock capture metadata was preserved
    assert result["qty_ordered"] == 20
    assert result["qty_received"] == 20
    assert result["cartons_received"] == 2

    # Verify structured evidence notes the fail-open reason
    evidence = json.loads(result["evidence_data"])
    assert "FAIL-OPEN ACTIVE" in evidence["decision_rationale"]
    assert evidence["individual_checks"][0]["verdict"] == "PENDING"

def test_api_fail_open_and_retry_workflow():
    # 1. Post inspection with simulate_fail_open = True
    payload = {
        "unit_id": "UNIT-RETRY-01",
        "po_number": "PO-RETRY-99",
        "po_line": 1,
        "supplier": "Supplier Retry",
        "sku": "BLUE-BOTTLE-001",
        "asin": "B0001BOTTLE",
        "product_title": "Blue Water Bottle",
        "spec_colour": "Blue",
        "spec_variant": "Standard",
        "cartons_ordered": 1,
        "cartons_received": 1,
        "units_per_carton_ordered": 24,
        "units_per_carton_counted": 24,
        "photo_refs": ["fixtures/receiving/clean_pallet.jpg"],
        "simulate_fail_open": True
    }
    
    resp = client.post("/api/inspect", json=payload, headers={"X-Org-ID": "org_demo_alpha"})
    assert resp.status_code == 200
    data = resp.json()
    record_id = data["record_id"]
    assert data["status"] == "pending_review"
    assert data["overall_verdict"] == "PENDING_REVIEW"

    # 2. Check record exists in DB with pending_review
    record = get_record_by_id_scoped(record_id, "org_demo_alpha")
    assert record is not None
    assert record["status"] == "pending_review"

    # 3. Warehouse line is NOT blocked; later, operator clicks Retry Inspection
    retry_resp = client.post(f"/api/records/{record_id}/retry", headers={"X-Org-ID": "org_demo_alpha"})
    assert retry_resp.status_code == 200
    retry_data = retry_resp.json()
    assert retry_data["retry_success"] is True
    assert retry_data["status"] == "processed"
    assert retry_data["overall_verdict"] == "PASS"

    # 4. Confirm DB record is updated to processed
    updated_record = get_record_by_id_scoped(record_id, "org_demo_alpha")
    assert updated_record["status"] == "processed"
    assert updated_record["overall_verdict"] == "PASS"

def test_malformed_spec_handled_gracefully():
    agent = ReceivingManagerAgent()
    # Unhandled corrupted spec (e.g. None or non-dict)
    # Pipeline catches exception and produces fail-open PENDING_REVIEW record
    result = agent.run_batch_receiving_inspection(
        org_id="org_demo_alpha",
        unit_id="UNIT-MALFORMED-01",
        po_line_spec=None,  # type: ignore
        captured_images=[]
    )
    assert result["status"] == "pending_review"
    assert result["overall_verdict"] == "PENDING_REVIEW"
    assert result["agent_confidence"] == 0.0
