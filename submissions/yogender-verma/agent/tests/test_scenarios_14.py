"""
Automated Test Suite for the 14 Required Test Scenarios (CUBE Track RCV#1)
Verifies:
1. Correct shipment
2. Short shipment
3. Extra units
4. Wrong SKU
5. Wrong variant
6. Crushed carton
7. Water-damaged carton
8. Torn packaging
9. Missing components
10. Ambiguous cases (UNCERTAIN)
11. Model failure / timeout (PENDING_REVIEW - Fail open)
12. Multi-image case
13. Operator override audit retention
14. Tenant isolation (Zero-row leak test)
"""

import pytest
import os
import json
from backend.agent import ReceivingManagerAgent
from backend.db import init_db, get_records_by_org, get_record_by_id_scoped, save_operator_override, get_db_connection
from backend.contract import generate_evidence_contract

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_scenario_01_correct_shipment():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1001", "po_line": 1, "supplier": "Supplier Alpha",
        "sku": "BLUE-BOTTLE-001", "asin": "B0001BOTTLE", "product_title": "Blue Water Bottle",
        "spec_colour": "Blue", "spec_variant": "Standard", "spec_components": "bottle; cap",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "qty_ordered": 24, "qty_received": 24,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-01", spec, ["fixtures/clean_pallet.jpg"])
    assert res["overall_verdict"] == "PASS"
    assert res["identity_match"] == "yes"
    assert res["carton_damage"] == "none"
    assert res["unit_damage"] == "none"

def test_scenario_02_short_shipment():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1002", "po_line": 1, "supplier": "Supplier Alpha",
        "sku": "BLUE-BOTTLE-001", "asin": "B0001BOTTLE", "product_title": "Blue Water Bottle",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 10,
        "qty_ordered": 24, "qty_received": 20,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-02", spec, ["fixtures/clean_pallet.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert res["qty_received"] < res["qty_ordered"]

def test_scenario_03_extra_units():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1003", "po_line": 1, "supplier": "Supplier Alpha",
        "sku": "BLUE-BOTTLE-001", "asin": "B0001BOTTLE", "product_title": "Blue Water Bottle",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 14,
        "qty_ordered": 24, "qty_received": 28,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-03", spec, ["fixtures/clean_pallet.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert res["qty_received"] > res["qty_ordered"]

def test_scenario_04_wrong_sku():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1004", "po_line": 1, "supplier": "Supplier Beta",
        "sku": "BLUE-BOTTLE-001", "asin": "B0001BOTTLE", "product_title": "Blue Water Bottle",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "qty_ordered": 12, "qty_received": 12,
        "override_identity_match": "no"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-04", spec, ["fixtures/wrong_sku.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert res["identity_match"] == "no"

def test_scenario_05_wrong_variant():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1005", "po_line": 1, "supplier": "Supplier Beta",
        "sku": "BLUE-BOTTLE-001", "asin": "B0001BOTTLE", "product_title": "Blue Water Bottle",
        "spec_colour": "Blue", "spec_variant": "Standard",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "qty_ordered": 12, "qty_received": 12,
        "override_quality_flags": ["wrong_colour", "wrong_variant"],
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-05", spec, ["fixtures/red_variant.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert "wrong_colour" in res["quality_flags"]

def test_scenario_06_crushed_carton():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1006", "po_line": 1, "supplier": "Supplier Gamma",
        "sku": "CANDLE-3PK", "asin": "B0002CANDLE", "product_title": "Soy Candle Set",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 6, "units_per_carton_counted": 6,
        "qty_ordered": 6, "qty_received": 6,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-06", spec, ["fixtures/pallet_crushing.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert res["carton_damage"] == "crushing"

def test_scenario_07_water_damaged_carton():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1007", "po_line": 1, "supplier": "Supplier Gamma",
        "sku": "CANDLE-3PK", "asin": "B0002CANDLE", "product_title": "Soy Candle Set",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 6, "units_per_carton_counted": 6,
        "qty_ordered": 6, "qty_received": 6,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-07", spec, ["fixtures/carton_water_soaked.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert res["carton_damage"] == "water"

def test_scenario_08_torn_packaging():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1008", "po_line": 1, "supplier": "Supplier Gamma",
        "sku": "TOWEL-BLU", "asin": "B0003TOWEL", "product_title": "Cotton Towel",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "qty_ordered": 12, "qty_received": 12,
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-08", spec, ["fixtures/packaging_tears.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert res["carton_damage"] == "tears"

def test_scenario_09_missing_components():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1009", "po_line": 1, "supplier": "Supplier Delta",
        "sku": "PROT-1KG", "asin": "B0004PROT", "product_title": "Whey Protein Tub",
        "spec_components": "tub; scoop",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "qty_ordered": 12, "qty_received": 12,
        "override_quality_flags": ["missing_components"],
        "override_identity_match": "yes"
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-09", spec, ["fixtures/missing_scoop.jpg"])
    assert res["overall_verdict"] == "FAIL"
    assert "missing_components" in res["quality_flags"]

def test_scenario_10_ambiguous_cases_uncertain():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1010", "po_line": 1, "supplier": "Supplier Delta",
        "sku": "SERUM-30ML", "asin": "B0005SERUM", "product_title": "Vitamin C Serum",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "qty_ordered": 12, "qty_received": 12
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-10", spec, ["fixtures/blur_dark_occluded.jpg"])
    assert res["overall_verdict"] == "UNCERTAIN"
    assert res["agent_confidence"] < 0.50

def test_scenario_11_model_failure_fail_open():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1011", "po_line": 1, "supplier": "Supplier Epsilon",
        "sku": "LAMP-LED", "asin": "B0006LAMP", "product_title": "LED Desk Lamp",
        "cartons_ordered": 1, "cartons_received": 1,
        "units_per_carton_ordered": 12, "units_per_carton_counted": 12,
        "qty_ordered": 12, "qty_received": 12
    }
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-11", spec, ["fixtures/lamp.jpg"], simling_failure=True)
    assert res["overall_verdict"] == "PENDING_REVIEW"
    assert res["status"] == "pending_review"

def test_scenario_12_multi_image_case():
    agent = ReceivingManagerAgent()
    spec = {
        "po_number": "PO-1012", "po_line": 1, "supplier": "Supplier Epsilon",
        "sku": "LAMP-LED", "asin": "B0006LAMP", "product_title": "LED Desk Lamp",
        "cartons_ordered": 2, "cartons_received": 2,
        "units_per_carton_ordered": 6, "units_per_carton_counted": 6,
        "qty_ordered": 12, "qty_received": 12,
        "override_identity_match": "yes"
    }
    photos = ["fixtures/pallet_overall.jpg", "fixtures/carton_label.jpg", "fixtures/unit_contents.jpg"]
    res = agent.run_batch_receiving_inspection("org_demo_alpha", "UNIT-TEST-12", spec, photos)
    assert res["overall_verdict"] == "PASS"
    evidence = json.loads(res["evidence_data"])
    assert len(evidence["what_received"]["photo_refs"]) == 3

def test_scenario_13_operator_override_audit():
    init_db()
    # Save base record RCV-0001
    records = get_records_by_org("org_demo_alpha")
    target_id = records[0]["record_id"]
    
    # Save override
    res = save_operator_override(
        record_id=target_id,
        org_id="org_demo_alpha",
        new_verdicts={"identity_match": "yes", "carton_damage": "none", "unit_damage": "none", "quality_flags": ""},
        operator_id="op_supervisor_99",
        reason="Visual packaging smudge misclassified as water damage. Item verified intact."
    )
    assert res["status"] == "success"
    assert res["new_overall_verdict"] == "PASS"

    # Verify both original and new exist in DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM operator_overrides WHERE record_id = ?", (target_id,))
    overrides = cursor.fetchall()
    assert len(overrides) >= 1
    assert overrides[0]["operator_id"] == "op_supervisor_99"
    conn.close()

def test_scenario_14_tenant_isolation_zero_leak():
    init_db()
    alpha_records = get_records_by_org("org_demo_alpha")
    assert len(alpha_records) > 0
    
    sample_alpha_id = alpha_records[0]["record_id"]
    
    # Query sample_alpha_id as org_demo_bravo
    leaked_record = get_record_by_id_scoped(sample_alpha_id, "org_demo_bravo")
    assert leaked_record is None  # Must return None (ZERO ROWS)
