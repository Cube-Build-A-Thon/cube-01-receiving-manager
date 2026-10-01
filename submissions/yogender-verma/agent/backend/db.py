import sqlite3
import csv
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "receiving_manager.db")
SAMPLE_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "receiving_sample.csv")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table for receiving records
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS receiving_records (
        record_id TEXT PRIMARY KEY,
        unit_id TEXT NOT NULL,
        shipment_id TEXT DEFAULT NULL,
        org_id TEXT NOT NULL,
        po_number TEXT NOT NULL,
        po_line INTEGER NOT NULL,
        supplier TEXT NOT NULL,
        sku TEXT NOT NULL,
        asin TEXT NOT NULL,
        product_title TEXT NOT NULL,
        spec_colour TEXT,
        spec_variant TEXT,
        spec_components TEXT,
        cartons_ordered INTEGER,
        cartons_received INTEGER,
        units_per_carton_ordered INTEGER,
        units_per_carton_counted INTEGER,
        qty_ordered INTEGER,
        qty_received INTEGER,
        identity_match TEXT DEFAULT 'uncertain',
        carton_damage TEXT DEFAULT 'none',
        unit_damage TEXT DEFAULT 'none',
        quality_flags TEXT DEFAULT '',
        photo_refs TEXT DEFAULT '',
        operator_id TEXT DEFAULT 'system',
        captured_at TEXT,
        overall_verdict TEXT DEFAULT 'UNCERTAIN',
        agent_confidence REAL DEFAULT 0.0,
        status TEXT DEFAULT 'processed',
        evidence_data TEXT
    );
    """)

    # Migration for existing databases that lack shipment_id column
    cursor.execute("PRAGMA table_info(receiving_records);")
    columns = [row[1] for row in cursor.fetchall()]
    if "shipment_id" not in columns:
        cursor.execute("ALTER TABLE receiving_records ADD COLUMN shipment_id TEXT DEFAULT NULL;")
    
    # Table for operator overrides (Engineering Rule: Overrides are data)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operator_overrides (
        override_id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT NOT NULL,
        org_id TEXT NOT NULL,
        original_identity_match TEXT,
        original_carton_damage TEXT,
        original_unit_damage TEXT,
        original_quality_flags TEXT,
        original_overall_verdict TEXT,
        new_identity_match TEXT,
        new_carton_damage TEXT,
        new_unit_damage TEXT,
        new_quality_flags TEXT,
        new_overall_verdict TEXT,
        operator_id TEXT NOT NULL,
        override_reason TEXT NOT NULL,
        overridden_at TEXT NOT NULL,
        FOREIGN KEY (record_id) REFERENCES receiving_records(record_id)
    );
    """)

    # Table for inspection attempts (Priority 2: Auditable Retry History)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inspection_attempts (
        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT NOT NULL,
        attempt_number INTEGER NOT NULL,
        org_id TEXT NOT NULL,
        unit_id TEXT NOT NULL,
        shipment_id TEXT,
        captured_at TEXT NOT NULL,
        overall_verdict TEXT NOT NULL,
        agent_confidence REAL DEFAULT 0.0,
        status TEXT NOT NULL,
        execution_mode TEXT NOT NULL,
        ai_provider TEXT,
        decision_rationale TEXT,
        evidence_data TEXT,
        photo_refs TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (record_id) REFERENCES receiving_records(record_id)
    );
    """)

    # Table for authoritative compliance rules (Engineering Rule 5)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channel_rules (
        rule_id TEXT PRIMARY KEY,
        channel TEXT NOT NULL,
        category TEXT NOT NULL,
        rule_name TEXT NOT NULL,
        description TEXT NOT NULL,
        authoritative_ref TEXT NOT NULL,
        check_type TEXT NOT NULL,
        pass_criteria TEXT NOT NULL
    );
    """)

    conn.commit()
    
    # Check if records table is empty; if so, seed from CSV
    cursor.execute("SELECT COUNT(*) FROM receiving_records;")
    count = cursor.fetchone()[0]
    if count == 0 and os.path.exists(SAMPLE_CSV_PATH):
        seed_db_from_csv(cursor)
        conn.commit()

    # Seed authoritative channel rules
    seed_authoritative_rules(cursor)
    conn.commit()

    conn.close()

def seed_db_from_csv(cursor):
    with open(SAMPLE_CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Determine initial overall verdict from check values
            id_match = row.get("identity_match", "uncertain")
            c_dmg = row.get("carton_damage", "none")
            u_dmg = row.get("unit_damage", "none")
            q_flags = row.get("quality_flags", "")

            if id_match == "no" or c_dmg in ["crushing", "water", "tears"] or u_dmg in ["crushing", "water", "tears"] or bool(q_flags):
                overall_verdict = "FAIL"
            elif id_match == "uncertain" or c_dmg == "uncertain" or u_dmg == "uncertain":
                overall_verdict = "UNCERTAIN"
            else:
                overall_verdict = "PASS"

            # Create evidence trail structure
            evidence_trail = {
                "what_received": {
                    "cartons_received": int(row.get("cartons_received", 0)),
                    "units_per_carton": int(row.get("units_per_carton_counted", 0)),
                    "total_qty_received": int(row.get("qty_received", 0)),
                    "photo_refs": row.get("photo_refs", "").split(";")
                },
                "what_expected": {
                    "po_number": row.get("po_number"),
                    "po_line": row.get("po_line"),
                    "sku": row.get("sku"),
                    "asin": row.get("asin"),
                    "product_title": row.get("product_title"),
                    "spec": {
                        "colour": row.get("spec_colour"),
                        "variant": row.get("spec_variant"),
                        "components": row.get("spec_components")
                    },
                    "cartons_ordered": int(row.get("cartons_ordered", 0)),
                    "qty_ordered": int(row.get("qty_ordered", 0))
                },
                "checks": [
                    {
                        "check_name": "Identity Match",
                        "verdict": "PASS" if id_match == "yes" else ("FAIL" if id_match == "no" else "UNCERTAIN"),
                        "confidence": 0.95 if id_match == "yes" else (0.92 if id_match == "no" else 0.45),
                        "details": f"Goods identity match against PO line: {id_match}"
                    },
                    {
                        "check_name": "Quantity Verification",
                        "verdict": "PASS" if int(row.get("qty_received", 0)) == int(row.get("qty_ordered", 0)) else "FAIL",
                        "confidence": 0.99,
                        "details": f"Expected {row.get('qty_ordered')} units, counted {row.get('qty_received')} units"
                    },
                    {
                        "check_name": "Carton Damage Inspection",
                        "verdict": "PASS" if c_dmg == "none" else ("UNCERTAIN" if c_dmg == "uncertain" else "FAIL"),
                        "confidence": 0.90,
                        "details": f"Carton damage status: {c_dmg}"
                    },
                    {
                        "check_name": "Unit Damage Inspection",
                        "verdict": "PASS" if u_dmg == "none" else ("UNCERTAIN" if u_dmg == "uncertain" else "FAIL"),
                        "confidence": 0.88,
                        "details": f"Unit damage status: {u_dmg}"
                    },
                    {
                        "check_name": "Spec Quality Check",
                        "verdict": "PASS" if not q_flags else "FAIL",
                        "confidence": 0.93,
                        "details": f"Quality flags detected: {q_flags}" if q_flags else "All specifications match agreed purchase order spec"
                    }
                ],
                "verdict": overall_verdict,
                "rationale": f"Overall verdict calculated as {overall_verdict} based on multi-check evaluation."
            }

            cursor.execute("""
            INSERT OR REPLACE INTO receiving_records (
                record_id, unit_id, shipment_id, org_id, po_number, po_line, supplier, sku, asin,
                product_title, spec_colour, spec_variant, spec_components,
                cartons_ordered, cartons_received, units_per_carton_ordered, units_per_carton_counted,
                qty_ordered, qty_received, identity_match, carton_damage, unit_damage,
                quality_flags, photo_refs, operator_id, captured_at, overall_verdict,
                agent_confidence, status, evidence_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["record_id"], row["unit_id"], row.get("shipment_id") or None, row["org_id"], row["po_number"], int(row["po_line"]),
                row["supplier"], row["sku"], row["asin"], row["product_title"],
                row.get("spec_colour", ""), row.get("spec_variant", ""), row.get("spec_components", ""),
                int(row.get("cartons_ordered", 0)), int(row.get("cartons_received", 0)),
                int(row.get("units_per_carton_ordered", 0)), int(row.get("units_per_carton_counted", 0)),
                int(row.get("qty_ordered", 0)), int(row.get("qty_received", 0)),
                id_match, c_dmg, u_dmg, q_flags, row.get("photo_refs", ""),
                row.get("operator_id", "op_default"), row.get("captured_at", datetime.utcnow().isoformat()),
                overall_verdict, 0.91, "processed", json.dumps(evidence_trail)
            ))

def seed_authoritative_rules(cursor):
    rules = [
        ("RULE-AMZ-01", "Amazon FBA", "Inbound Carton Integrity", "Carton Structural Compression Standard",
         "Carton crushing > 10% volume or moisture absorption is unacceptable.",
         "Amazon Inbound Logistics Spec 2026 §4.2", "carton_damage", "carton_damage in ['none']"),
        ("RULE-AMZ-02", "Amazon FBA", "Unit Variant & Barcode", "FNSKU & Variant Spec Matching",
         "SKU color and size variant must exactly equal purchase order specification line.",
         "Amazon Merchant Manual §9.1", "quality_flags", "quality_flags does not contain wrong_colour or wrong_variant"),
        ("RULE-3PL-01", "Global 3PL", "Quantity Tolerance", "Strict Inbound Unit Count Standard",
         "Discrepancy between cartons ordered vs cartons received triggers instant supplier claim notice.",
         "Warehouse Standard Operating Procedure RCV-201", "quantity_verification", "qty_received == qty_ordered"),
        ("RULE-AMZ-03", "Amazon FBA", "Moisture / Water Damage", "Zero Water Intrusion Rule",
         "Any carton or unit with moisture spots or water damage must be rejected as UNCERTAIN or FAIL.",
         "Amazon Prep & Receiving Policy §12.4", "carton_damage", "carton_damage != 'water' and unit_damage != 'water'")
    ]
    for r in rules:
        cursor.execute("""
        INSERT OR REPLACE INTO channel_rules (
            rule_id, channel, category, rule_name, description, authoritative_ref, check_type, pass_criteria
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, r)

# Tenancy Isolation Enforcer (Engineering Rule 1)
def get_records_by_org(org_id: str) -> List[Dict[str, Any]]:
    """Returns records ONLY belonging to org_id. Scoped row-level security."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receiving_records WHERE org_id = ? ORDER BY captured_at DESC", (org_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_record_by_id_scoped(record_id: str, org_id: str) -> Optional[Dict[str, Any]]:
    """Returns record by ID ONLY if it matches org_id. Prevents cross-tenant guessable key leaks."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receiving_records WHERE record_id = ? AND org_id = ?", (record_id, org_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_operator_override(record_id: str, org_id: str, new_verdicts: Dict[str, Any], operator_id: str, reason: str) -> Dict[str, Any]:
    """Logs operator override without deleting original data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Scoped fetch
    cursor.execute("SELECT * FROM receiving_records WHERE record_id = ? AND org_id = ?", (record_id, org_id))
    record = cursor.fetchone()
    if not record:
        conn.close()
        raise PermissionError("Access denied or record not found for this tenant.")

    rec_dict = dict(record)
    
    # Calculate new overall verdict
    new_id_match = new_verdicts.get("identity_match", rec_dict["identity_match"])
    new_c_dmg = new_verdicts.get("carton_damage", rec_dict["carton_damage"])
    new_u_dmg = new_verdicts.get("unit_damage", rec_dict["unit_damage"])
    new_q_flags = new_verdicts.get("quality_flags", rec_dict["quality_flags"])
    
    if new_id_match == "no" or new_c_dmg in ["crushing", "water", "tears"] or new_u_dmg in ["crushing", "water", "tears"] or bool(new_q_flags):
        new_overall = "FAIL"
    elif new_id_match == "uncertain" or new_c_dmg == "uncertain" or new_u_dmg == "uncertain":
        new_overall = "UNCERTAIN"
    else:
        new_overall = "PASS"

    # Insert into audit table
    now_str = datetime.utcnow().isoformat()
    cursor.execute("""
    INSERT INTO operator_overrides (
        record_id, org_id, original_identity_match, original_carton_damage, original_unit_damage,
        original_quality_flags, original_overall_verdict, new_identity_match, new_carton_damage,
        new_unit_damage, new_quality_flags, new_overall_verdict, operator_id, override_reason, overridden_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record_id, org_id, rec_dict["identity_match"], rec_dict["carton_damage"], rec_dict["unit_damage"],
        rec_dict["quality_flags"], rec_dict["overall_verdict"],
        new_id_match, new_c_dmg, new_u_dmg, new_q_flags, new_overall, operator_id, reason, now_str
    ))

    # Update primary record
    cursor.execute("""
    UPDATE receiving_records SET
        identity_match = ?,
        carton_damage = ?,
        unit_damage = ?,
        quality_flags = ?,
        overall_verdict = ?,
        operator_id = ?
    WHERE record_id = ? AND org_id = ?
    """, (new_id_match, new_c_dmg, new_u_dmg, new_q_flags, new_overall, operator_id, record_id, org_id))

    conn.commit()
    conn.close()

    return {"status": "success", "override_recorded": True, "new_overall_verdict": new_overall}
    
def record_inspection_attempt(
    record_id: str,
    org_id: str,
    unit_id: str,
    shipment_id: Optional[str],
    overall_verdict: str,
    agent_confidence: float,
    status: str,
    execution_mode: str,
    ai_provider: Optional[str] = None,
    decision_rationale: Optional[str] = None,
    evidence_data: Optional[str] = None,
    photo_refs: Optional[str] = None,
    captured_at: Optional[str] = None
) -> int:
    """
    Appends an immutable inspection attempt record.
    Preserves original failures, API timeouts, and UNCERTAIN verdicts for auditability (Priority 2).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Determine next attempt number for this record within this tenant org
    cursor.execute(
        "SELECT COUNT(*) FROM inspection_attempts WHERE record_id = ? AND org_id = ?",
        (record_id, org_id)
    )
    count = cursor.fetchone()[0]
    attempt_num = count + 1
    
    now_str = datetime.utcnow().isoformat()
    cap_str = captured_at or now_str
    
    cursor.execute("""
    INSERT INTO inspection_attempts (
        record_id, attempt_number, org_id, unit_id, shipment_id,
        captured_at, overall_verdict, agent_confidence, status,
        execution_mode, ai_provider, decision_rationale, evidence_data,
        photo_refs, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record_id, attempt_num, org_id, unit_id, shipment_id,
        cap_str, overall_verdict, agent_confidence, status,
        execution_mode, ai_provider, decision_rationale, evidence_data,
        photo_refs, now_str
    ))
    conn.commit()
    attempt_id = cursor.lastrowid
    conn.close()
    return attempt_id

def get_attempts_by_record(record_id: str, org_id: str) -> List[Dict[str, Any]]:
    """
    Returns all inspection attempts for a record, strictly scoped by tenant org_id.
    Prevents cross-tenant attempt leaks.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM inspection_attempts
    WHERE record_id = ? AND org_id = ?
    ORDER BY attempt_number ASC
    """, (record_id, org_id))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print("Database initialized and seeded successfully.")
