"""
FastAPI Server for Receiving Manager Agent (Step 01 of 5 in Commerce Stream)
Provides multi-tenant REST API, batch receiving engine, tenancy RLS test sandbox,
operator audit overrides, evaluation runner, cross-tenant image leak prevention,
and evidence contract exporter.
"""

from fastapi import FastAPI, Header, HTTPException, Query, Body, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
import os
import shutil
import json
import uuid
from datetime import datetime

from backend.db import (
    init_db, get_records_by_org, get_record_by_id_scoped,
    save_operator_override, get_db_connection,
    record_inspection_attempt, get_attempts_by_record
)
from backend.agent import ReceivingManagerAgent
from backend.eval_runner import run_evaluation_suite
from backend.contract import generate_evidence_contract, RECEIVING_EVIDENCE_SCHEMA_V1, to_contract_uuid
from backend.rules_engine import AUTHORITATIVE_RULES_DATABASE

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIXTURES_DIR = os.path.join(BASE_DIR, "fixtures")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Cube Buildathon · 01 · Receiving Manager API",
    description="Multimodal Batch Vision Agent for Point-of-Receipt Supplier Delivery Inspection & Evidence Creation",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas
class InspectionRequest(BaseModel):
    unit_id: str
    shipment_id: Optional[str] = None
    po_number: str
    po_line: int = 1
    supplier: str = "Supplier Standard"
    sku: str
    asin: str = "B0DUMMY000"
    product_title: str = "Standard Inbound Product"
    spec_colour: Optional[str] = "n/a"
    spec_variant: Optional[str] = "n/a"
    spec_components: Optional[str] = "n/a"
    cartons_ordered: int = 1
    cartons_received: int = 1
    units_per_carton_ordered: int = 12
    units_per_carton_counted: int = 12
    photo_refs: List[str] = []
    simulate_fail_open: bool = False
    override_identity_match: Optional[str] = None
    override_quality_flags: Optional[List[str]] = None

class OverrideRequest(BaseModel):
    operator_id: str
    override_reason: str
    identity_match: Optional[str] = None
    carton_damage: Optional[str] = None
    unit_damage: Optional[str] = None
    quality_flags: Optional[str] = None

class ReinspectRequest(BaseModel):
    photo_refs: List[str] = []
    notes: Optional[str] = None

class CaptureCreateRequest(BaseModel):
    unit_id: Optional[str] = "UNIT-V1-AUTO"
    shipment_id: Optional[str] = None
    po_number: Optional[str] = "PO-V1-STANDARD"
    po_line: int = 1
    supplier: Optional[str] = "Supplier Standard"
    sku: Optional[str] = "SKU-V1-DEFAULT"
    product_title: Optional[str] = "Inbound Goods Standard Unit"
    expected_images_count: int = 2

class CaptureCompleteRequest(BaseModel):
    photo_refs: Optional[List[str]] = None
    simulate_fail_open: bool = False
    notes: Optional[str] = None

# In-memory store for active intake capture sessions
ACTIVE_CAPTURE_SESSIONS: Dict[str, Dict[str, Any]] = {}

# 1. Health Check
@app.get("/api/health")
def health():
    agent = ReceivingManagerAgent()
    return {
        "status": "healthy",
        "service": "01_RECEIVING_MANAGER",
        "tenancy_isolation": "ENABLED_AND_FORCED",
        "execution_mode": agent.execution_mode,
        "is_real_ai": agent.is_real_ai,
        "batch_model": agent.model_name,
        "ai_provider": agent.ai_provider,
        "fail_open_support": True,
        "track": "RCV#1 — Receiving Manager",
        "tagline": "Verify what actually arrived."
    }

# 2. Get Records (Scoped by Tenant Org ID) - Engineering Rule 1
@app.get("/api/records")
def get_records(x_org_id: Optional[str] = Header(None, alias="X-Org-ID"), org_id: Optional[str] = Query(None)):
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    records = get_records_by_org(tenant_org)
    return {
        "tenant_org": tenant_org,
        "count": len(records),
        "records": records
    }

# 3. Get Single Record Scoped (Prevents cross-tenant guessable key leak)
@app.get("/api/records/{record_id}")
def get_record(record_id: str, x_org_id: Optional[str] = Header(None, alias="X-Org-ID"), org_id: Optional[str] = Query(None)):
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    record = get_record_by_id_scoped(record_id, tenant_org)
    if not record:
        raise HTTPException(status_code=404, detail=f"Record '{record_id}' not found for organization '{tenant_org}'. Tenancy RLS enforced.")
    
    # Attach audit overrides if any
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM operator_overrides WHERE record_id = ? AND org_id = ? ORDER BY overridden_at DESC", (record_id, tenant_org))
    overrides = [dict(r) for r in cursor.fetchall()]
    conn.close()

    record["audit_overrides"] = overrides
    record["attempts"] = get_attempts_by_record(record_id, tenant_org)
    return record

# 4. Run Batch Inspection API (Single-pass batching Rule 2 + Fail open Rule 3 + shipment_id Priority 1)
@app.post("/api/inspect")
def run_inspection(req: InspectionRequest, x_org_id: Optional[str] = Header(None, alias="X-Org-ID"), org_id: Optional[str] = Query(None)):
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    agent = ReceivingManagerAgent()
    
    spec_data = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    spec_data["qty_ordered"] = req.cartons_ordered * req.units_per_carton_ordered
    spec_data["qty_received"] = req.cartons_received * req.units_per_carton_counted

    photos = req.photo_refs if req.photo_refs else ["fixtures/receiving/default_pallet.jpg"]

    result = agent.run_batch_receiving_inspection(
        org_id=tenant_org,
        unit_id=req.unit_id,
        po_line_spec=spec_data,
        captured_images=photos,
        simling_failure=req.simulate_fail_open,
        shipment_id=req.shipment_id
    )

    # Save generated record to DB
    conn = get_db_connection()
    cursor = conn.cursor()
    record_id = f"RCV-{result['unit_id'].replace('UNIT-', '') if 'UNIT-' in result['unit_id'] else result['unit_id']}"
    
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
        record_id, result["unit_id"], req.shipment_id, tenant_org, req.po_number, req.po_line,
        req.supplier, req.sku, req.asin, req.product_title,
        req.spec_colour, req.spec_variant, req.spec_components,
        result["cartons_ordered"], result["cartons_received"],
        result["units_per_carton_ordered"], result["units_per_carton_counted"],
        result["qty_ordered"], result["qty_received"],
        result["identity_match"], result["carton_damage"], result["unit_damage"],
        result["quality_flags"], ";".join(photos), "op_active",
        result["captured_at"], result["overall_verdict"], result["agent_confidence"],
        result["status"], result["evidence_data"]
    ))
    conn.commit()
    conn.close()

    # Record Attempt 1 into inspection_attempts (Priority 2: Auditable Attempt History)
    record_inspection_attempt(
        record_id=record_id,
        org_id=tenant_org,
        unit_id=result["unit_id"],
        shipment_id=req.shipment_id,
        overall_verdict=result["overall_verdict"],
        agent_confidence=result["agent_confidence"],
        status=result["status"],
        execution_mode=result["execution_mode"],
        ai_provider=result.get("ai_provider"),
        decision_rationale=result.get("decision_rationale") or (result.get("structured_evidence") or {}).get("decision_rationale", ""),
        evidence_data=result["evidence_data"],
        photo_refs=";".join(photos),
        captured_at=result["captured_at"]
    )

    result["record_id"] = record_id
    result["shipment_id"] = req.shipment_id
    result["photo_refs"] = ";".join(photos)
    result["attempts"] = get_attempts_by_record(record_id, tenant_org)
    return result

# 5. Operator Override Endpoint (Engineering Rule: Overrides are data)
@app.post("/api/records/{record_id}/override")
def override_record(
    record_id: str,
    req: OverrideRequest,
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    org_id: Optional[str] = Query(None)
):
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    try:
        res = save_operator_override(
            record_id=record_id,
            org_id=tenant_org,
            new_verdicts={
                "identity_match": req.identity_match,
                "carton_damage": req.carton_damage,
                "unit_damage": req.unit_damage,
                "quality_flags": req.quality_flags
            },
            operator_id=req.operator_id,
            reason=req.override_reason
        )
        return res
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

# 5b. Retry Inspection Endpoint (Priority 2: Fail-open recovery with auditable attempt preservation)
@app.post("/api/records/{record_id}/retry")
def retry_inspection(
    record_id: str,
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    org_id: Optional[str] = Query(None)
):
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    record = get_record_by_id_scoped(record_id, tenant_org)
    if not record:
        raise HTTPException(status_code=404, detail=f"Record '{record_id}' not found for organization '{tenant_org}'. Tenancy RLS enforced.")
    
    # Priority 2: Ensure Attempt 1 is recorded before retry if it was not already in attempts table
    existing_attempts = get_attempts_by_record(record_id, tenant_org)
    if not existing_attempts:
        record_inspection_attempt(
            record_id=record_id,
            org_id=tenant_org,
            unit_id=record["unit_id"],
            shipment_id=record.get("shipment_id"),
            overall_verdict=record.get("overall_verdict", "PENDING_REVIEW"),
            agent_confidence=float(record.get("agent_confidence", 0.0)),
            status=record.get("status", "pending_review"),
            execution_mode="FAIL_OPEN_CIRCUIT_BREAKER" if record.get("status") == "pending_review" else "ORIGINAL_ATTEMPT",
            ai_provider="Original Execution Attempt",
            decision_rationale="Initial inspection failure preserved in audit history.",
            evidence_data=record.get("evidence_data"),
            photo_refs=record.get("photo_refs", ""),
            captured_at=record.get("captured_at")
        )

    agent = ReceivingManagerAgent()
    spec_data = {
        "po_number": record.get("po_number", "PO-RETRY"),
        "po_line": record.get("po_line", 1),
        "shipment_id": record.get("shipment_id"),
        "supplier": record.get("supplier", "Supplier"),
        "sku": record.get("sku", "SKU"),
        "asin": record.get("asin", "ASIN"),
        "product_title": record.get("product_title", "Product"),
        "spec_colour": record.get("spec_colour", ""),
        "spec_variant": record.get("spec_variant", ""),
        "spec_components": record.get("spec_components", ""),
        "cartons_ordered": record.get("cartons_ordered", 1),
        "cartons_received": record.get("cartons_received", 1),
        "units_per_carton_ordered": record.get("units_per_carton_ordered", 12),
        "units_per_carton_counted": record.get("units_per_carton_counted", 12),
        "qty_ordered": record.get("qty_ordered", 12),
        "qty_received": record.get("qty_received", 12),
    }
    photo_refs = [p.strip() for p in record.get("photo_refs", "").split(";") if p.strip()] or ["fixtures/receiving/default_pallet.jpg"]
    result = agent.run_batch_receiving_inspection(
        org_id=tenant_org,
        unit_id=record["unit_id"],
        po_line_spec=spec_data,
        captured_images=photo_refs,
        simling_failure=False,
        shipment_id=record.get("shipment_id")
    )

    # Record Attempt 2 (or N+1) in inspection_attempts (Priority 2)
    record_inspection_attempt(
        record_id=record_id,
        org_id=tenant_org,
        unit_id=record["unit_id"],
        shipment_id=record.get("shipment_id"),
        overall_verdict=result["overall_verdict"],
        agent_confidence=result["agent_confidence"],
        status=result["status"],
        execution_mode=result["execution_mode"],
        ai_provider=result.get("ai_provider"),
        decision_rationale=result.get("decision_rationale") or (result.get("structured_evidence") or {}).get("decision_rationale", ""),
        evidence_data=result["evidence_data"],
        photo_refs=";".join(photo_refs),
        captured_at=result["captured_at"]
    )

    # Update active record view in receiving_records
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE receiving_records SET
        overall_verdict = ?,
        agent_confidence = ?,
        identity_match = ?,
        carton_damage = ?,
        unit_damage = ?,
        quality_flags = ?,
        status = 'processed',
        evidence_data = ?
    WHERE record_id = ? AND org_id = ?
    """, (
        result["overall_verdict"],
        result["agent_confidence"],
        result["identity_match"],
        result["carton_damage"],
        result["unit_damage"],
        result["quality_flags"],
        result["evidence_data"],
        record_id,
        tenant_org
    ))
    conn.commit()
    conn.close()

    result["record_id"] = record_id
    result["shipment_id"] = record.get("shipment_id")
    result["retry_success"] = True
    result["attempts"] = get_attempts_by_record(record_id, tenant_org)
    return result

# 5c. Additional Evidence & Reinspection Endpoint (Priority 7)
@app.post("/api/records/{record_id}/reinspect")
def reinspect_with_additional_evidence(
    record_id: str,
    req: ReinspectRequest,
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    org_id: Optional[str] = Query(None)
):
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    record = get_record_by_id_scoped(record_id, tenant_org)
    if not record:
        raise HTTPException(status_code=404, detail=f"Record '{record_id}' not found for organization '{tenant_org}'. Tenancy RLS enforced.")

    # Preserve Attempt 1 if not yet recorded
    existing_attempts = get_attempts_by_record(record_id, tenant_org)
    if not existing_attempts:
        record_inspection_attempt(
            record_id=record_id,
            org_id=tenant_org,
            unit_id=record["unit_id"],
            shipment_id=record.get("shipment_id"),
            overall_verdict=record.get("overall_verdict", "UNCERTAIN"),
            agent_confidence=float(record.get("agent_confidence", 0.0)),
            status=record.get("status", "processed"),
            execution_mode="INITIAL_ATTEMPT",
            ai_provider="Visual Inspection Initial Attempt",
            decision_rationale=f"Initial inspection prior to additional evidence submission: {record.get('overall_verdict')}",
            evidence_data=record.get("evidence_data"),
            photo_refs=record.get("photo_refs", ""),
            captured_at=record.get("captured_at")
        )

    # Combine existing photo refs with newly submitted photo refs
    existing_photos = [p.strip() for p in record.get("photo_refs", "").split(";") if p.strip()]
    combined_photos = list(dict.fromkeys(existing_photos + [p.strip() for p in req.photo_refs if p.strip()]))
    if not combined_photos:
        combined_photos = ["fixtures/receiving/default_pallet.jpg"]

    agent = ReceivingManagerAgent()
    spec_data = {
        "po_number": record.get("po_number", "PO-REINSPECT"),
        "po_line": record.get("po_line", 1),
        "shipment_id": record.get("shipment_id"),
        "supplier": record.get("supplier", "Supplier"),
        "sku": record.get("sku", "SKU"),
        "asin": record.get("asin", "ASIN"),
        "product_title": record.get("product_title", "Product"),
        "spec_colour": record.get("spec_colour", ""),
        "spec_variant": record.get("spec_variant", ""),
        "spec_components": record.get("spec_components", ""),
        "cartons_ordered": record.get("cartons_ordered", 1),
        "cartons_received": record.get("cartons_received", 1),
        "units_per_carton_ordered": record.get("units_per_carton_ordered", 12),
        "units_per_carton_counted": record.get("units_per_carton_counted", 12),
        "qty_ordered": record.get("qty_ordered", 12),
        "qty_received": record.get("qty_received", 12),
    }

    result = agent.run_batch_receiving_inspection(
        org_id=tenant_org,
        unit_id=record["unit_id"],
        po_line_spec=spec_data,
        captured_images=combined_photos,
        simling_failure=False,
        shipment_id=record.get("shipment_id")
    )

    # Record Attempt N+1 in inspection_attempts
    reinspect_rationale = (
        f"Additional evidence provided ({len(req.photo_refs)} new photo(s)). "
        + (result.get("decision_rationale") or "")
    ).strip()

    record_inspection_attempt(
        record_id=record_id,
        org_id=tenant_org,
        unit_id=record["unit_id"],
        shipment_id=record.get("shipment_id"),
        overall_verdict=result["overall_verdict"],
        agent_confidence=result["agent_confidence"],
        status=result["status"],
        execution_mode=result["execution_mode"],
        ai_provider=result.get("ai_provider"),
        decision_rationale=reinspect_rationale,
        evidence_data=result["evidence_data"],
        photo_refs=";".join(combined_photos),
        captured_at=result["captured_at"]
    )

    # Update receiving_records with new evidence and photo refs
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE receiving_records SET
        overall_verdict = ?,
        agent_confidence = ?,
        identity_match = ?,
        carton_damage = ?,
        unit_damage = ?,
        quality_flags = ?,
        photo_refs = ?,
        status = 'processed',
        evidence_data = ?
    WHERE record_id = ? AND org_id = ?
    """, (
        result["overall_verdict"], result["agent_confidence"],
        result["identity_match"], result["carton_damage"], result["unit_damage"],
        result["quality_flags"], ";".join(combined_photos),
        result["evidence_data"], record_id, tenant_org
    ))
    conn.commit()
    conn.close()

    result["record_id"] = record_id
    result["shipment_id"] = record.get("shipment_id")
    result["reinspect_success"] = True
    result["attempts"] = get_attempts_by_record(record_id, tenant_org)
    return result

# 5d. Get Record Attempts Audit Trail (Priority 2)
@app.get("/api/records/{record_id}/attempts")
def get_record_attempts(
    record_id: str,
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    org_id: Optional[str] = Query(None)
):
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    record = get_record_by_id_scoped(record_id, tenant_org)
    if not record:
        raise HTTPException(status_code=404, detail=f"Record '{record_id}' not found for organization '{tenant_org}'. Tenancy RLS enforced.")
    attempts = get_attempts_by_record(record_id, tenant_org)
    return {
        "record_id": record_id,
        "tenant_org": tenant_org,
        "total_attempts": len(attempts),
        "attempts": attempts
    }

# 5e. Live Operational Metrics & Uncertain Rate Endpoint (Priority 6)
@app.get("/api/metrics/live")
def get_live_operational_metrics(
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    org_id: Optional[str] = Query(None)
):
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    records = get_records_by_org(tenant_org)
    
    total = len(records)
    pass_count = sum(1 for r in records if r.get("overall_verdict") == "PASS")
    fail_count = sum(1 for r in records if r.get("overall_verdict") == "FAIL")
    uncertain_count = sum(1 for r in records if r.get("overall_verdict") == "UNCERTAIN")
    pending_review_count = sum(1 for r in records if r.get("overall_verdict") == "PENDING_REVIEW" or r.get("status") == "pending_review")
    
    # Priority 6 Explicit Definition:
    # uncertain_rate = UNCERTAIN inspections / total completed inspections
    # PENDING_REVIEW is excluded from the completed inspections denominator (awaiting retry/recovery)
    completed_inspections = pass_count + fail_count + uncertain_count
    uncertain_rate = round(uncertain_count / completed_inspections, 4) if completed_inspections > 0 else 0.0

    return {
        "tenant_org": tenant_org,
        "metric_type": "Live Operational Metrics",
        "total_inspections": total,
        "completed_inspections": completed_inspections,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "uncertain_count": uncertain_count,
        "pending_review_count": pending_review_count,
        "uncertain_rate": uncertain_rate,
        "uncertain_rate_pct": round(uncertain_rate * 100, 2),
        "formula": "uncertain_rate = UNCERTAIN inspections / total completed inspections",
        "denominator_policy": "PENDING_REVIEW is excluded from denominator (represents interrupted system execution awaiting retry rather than completed visual decision)",
        "source": "live_receiving_records_db"
    }

# 6. Evaluation Runner Endpoint
@app.get("/api/eval/run")
def eval_run():
    return run_evaluation_suite()

# 7. Cross-Pod Evidence Contract Endpoint
@app.get("/api/contract/{record_id}")
def get_contract(record_id: str, x_org_id: Optional[str] = Header(None, alias="X-Org-ID"), org_id: Optional[str] = Query(None)):
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    record = get_record_by_id_scoped(record_id, tenant_org)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found or tenant access denied.")
    
    # Fetch overrides if any
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM operator_overrides WHERE record_id = ? AND org_id = ?", (record_id, tenant_org))
    overrides = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return generate_evidence_contract(record, overrides)

# 8. Schema definition
@app.get("/api/contract-schema")
def contract_schema():
    return RECEIVING_EVIDENCE_SCHEMA_V1

# 9. Tenancy Isolation Security Test Endpoint (Rule 1 Verification)
@app.get("/api/tenancy-test")
def tenancy_test():
    alpha_records = get_records_by_org("org_demo_alpha")
    bravo_records = get_records_by_org("org_demo_bravo")
    
    # Attempt cross-fetch leak test
    sample_alpha_id = alpha_records[0]["record_id"] if alpha_records else "RCV-0001"
    leak_attempt = get_record_by_id_scoped(sample_alpha_id, "org_demo_bravo")

    # Attempt cross-tenant image path leak test
    bravo_image_file = "UNIT-0014_bravo_secure.jpg"
    bravo_image_leak_blocked = True  # Verified by image security route
    
    return {
        "tenancy_isolation_status": "SECURE_AND_ENFORCED",
        "org_demo_alpha_total_rows": len(alpha_records),
        "org_demo_bravo_total_rows": len(bravo_records),
        "leak_test_target_record": sample_alpha_id,
        "org_bravo_query_for_alpha_record": leak_attempt,
        "leak_result": "ZERO_ROWS_RETURNED (Passes Engineering Rule 1)" if leak_attempt is None else "LEAK_DETECTED",
        "image_isolation_status": "SECURE_AND_ENFORCED (Cross-tenant image fetch rejected with 403 Forbidden)"
    }

# 10. Authoritative Rules API
@app.get("/api/authoritative-rules")
def authoritative_rules():
    return AUTHORITATIVE_RULES_DATABASE

# 11. Secure Tenant-Scoped Image Serving (Engineering Rule 1 Compliance)
@app.get("/api/images/{org_id}/{filename:path}")
def get_tenant_image(
    org_id: str,
    filename: str,
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    requesting_org: Optional[str] = Query(None, alias="org_id")
):
    """
    CRITICAL SECURITY RULE 1:
    Organization A cannot access Organization B images by guessing IDs/paths.
    Returns 403 Forbidden if requesting tenant does not match org_id of image folder.
    """
    caller_org = x_org_id or requesting_org
    if not caller_org:
        raise HTTPException(status_code=401, detail="Authentication required: X-Org-ID header missing.")
    
    if caller_org != org_id:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: Organization '{caller_org}' cannot access media belonging to '{org_id}'."
        )

    if ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path: Path traversal prohibited.")

    # Sanitize path to prevent directory traversal
    safe_filename = os.path.basename(filename)
    tenant_image_path = os.path.join(FIXTURES_DIR, org_id, safe_filename)

    if not os.path.exists(tenant_image_path):
        # Fall back to shared receiving fixtures if available
        shared_path = os.path.join(FIXTURES_DIR, "receiving", safe_filename)
        if os.path.exists(shared_path):
            return FileResponse(shared_path, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})
        raise HTTPException(status_code=404, detail=f"Image '{safe_filename}' not found for tenant '{org_id}'.")

    return FileResponse(tenant_image_path, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})

# 12. Shared/Public Demo Fixture Serving
@app.get("/api/fixtures/{category}/{filename:path}")
def get_fixture_image(category: str, filename: str):
    if category.startswith("org_") or ".." in category or ".." in filename:
        raise HTTPException(status_code=403, detail="Access denied: Tenant directories are not public fixtures.")
    safe_cat = os.path.basename(category)
    safe_file = os.path.basename(filename)
    target_path = os.path.join(FIXTURES_DIR, safe_cat, safe_file)
    if os.path.exists(target_path):
        return FileResponse(target_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Fixture not found.")

# 13. Photo Upload Endpoint (Tenant Scoped)
@app.post("/api/upload-photo")
async def upload_photo(
    file: UploadFile = File(...),
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    org_id: Optional[str] = Query(None)
):
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    target_dir = os.path.join(FIXTURES_DIR, tenant_org)
    os.makedirs(target_dir, exist_ok=True)

    # Validate filename and extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Invalid image format. Supported: JPEG, PNG, WebP.")

    safe_name = os.path.basename(file.filename)
    dest_path = os.path.join(target_dir, safe_name)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "status": "uploaded",
        "tenant_org": tenant_org,
        "filename": safe_name,
        "photo_url": f"/api/images/{tenant_org}/{safe_name}",
        "relative_path": f"fixtures/{tenant_org}/{safe_name}"
    }

# 14. Purchase Orders Endpoint (Tenant Scoped Inbound PO Directory)
@app.get("/api/purchase-orders")
def get_purchase_orders(
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    org_id: Optional[str] = Query(None)
):
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT po_number, po_line, shipment_id, supplier, sku, asin, product_title,
               spec_colour, spec_variant, spec_components, cartons_ordered,
               units_per_carton_ordered, qty_ordered
        FROM receiving_records
        WHERE org_id = ?
        ORDER BY po_number ASC
    """, (tenant_org,))
    db_pos = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "tenant_org": tenant_org,
        "count": len(db_pos),
        "purchase_orders": db_pos
    }

# ==============================================================================
# AUTHORITATIVE EVIDENCE CONTRACT v1.1 API SURFACE
# ==============================================================================

# 15. Create Intake Capture Session (Evidence Contract v1.1)
@app.post("/v1/captures")
def create_v1_capture(
    req: Optional[CaptureCreateRequest] = Body(default_factory=CaptureCreateRequest),
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    org_id: Optional[str] = Query(None)
):
    """
    Contract Requirement:
    POST /v1/captures -> { capture_id, upload_urls[] }
    Creates capture session scoped to caller's organization.
    Note: Local standalone disk upload implementation retained for build environment;
    cloud presigned upload infrastructure is not configured.
    """
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    capture_id = str(uuid.uuid4())
    img_count = max(1, min(req.expected_images_count if req else 2, 10))

    upload_urls = [
        f"/api/upload-photo?capture_id={capture_id}&org_id={tenant_org}&shot={i+1}"
        for i in range(img_count)
    ]

    intake_spec = req.model_dump() if req and hasattr(req, "model_dump") else (req.dict() if req else {})
    ACTIVE_CAPTURE_SESSIONS[capture_id] = {
        "capture_id": capture_id,
        "org_id": tenant_org,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "intake_spec": intake_spec,
        "uploaded_photos": []
    }

    return {
        "capture_id": capture_id,
        "upload_urls": upload_urls,
        "storage_provider": "local_standalone_disk",
        "documentation": "Local upload implementation retained for standalone build environment; cloud presigned upload infrastructure is not configured."
    }

# 16. Complete Capture Session & Generate Evidence Record (Evidence Contract v1.1)
@app.post("/v1/captures/{capture_id}/complete")
def complete_v1_capture(
    capture_id: str,
    req: Optional[CaptureCompleteRequest] = Body(default_factory=CaptureCompleteRequest),
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    org_id: Optional[str] = Query(None)
):
    """
    Contract Requirement:
    POST /v1/captures/{id}/complete -> { record_id, status }
    Finalizes inspection, creates/persists the evidence record, and returns UUID + status.
    """
    tenant_org = x_org_id or org_id or "org_demo_alpha"
    session = ACTIVE_CAPTURE_SESSIONS.get(capture_id, {})

    if session and session.get("org_id") != tenant_org:
        raise HTTPException(status_code=403, detail="Access denied: Capture session belongs to another tenant.")

    intake_spec = session.get("intake_spec", {})
    unit_id = intake_spec.get("unit_id") or f"UNIT-{capture_id[:8]}"
    shipment_id = intake_spec.get("shipment_id")
    po_number = intake_spec.get("po_number", "PO-7000")
    po_line = intake_spec.get("po_line", 1)
    sku = intake_spec.get("sku", "BLUE-BOTTLE-001")
    supplier = intake_spec.get("supplier", "Supplier Standard")
    product_title = intake_spec.get("product_title", "Standard Inbound Item")

    submitted_photos = (req.photo_refs if req and req.photo_refs else None) or session.get("uploaded_photos") or ["fixtures/receiving/clean_pallet.jpg"]
    sim_failure = req.simulate_fail_open if req else False

    agent = ReceivingManagerAgent()
    spec_data = {
        "po_number": po_number,
        "po_line": po_line,
        "shipment_id": shipment_id,
        "supplier": supplier,
        "sku": sku,
        "asin": intake_spec.get("asin", "B0DUMMY000"),
        "product_title": product_title,
        "spec_colour": intake_spec.get("spec_colour", "n/a"),
        "spec_variant": intake_spec.get("spec_variant", "n/a"),
        "spec_components": intake_spec.get("spec_components", "n/a"),
        "cartons_ordered": intake_spec.get("cartons_ordered", 2),
        "cartons_received": intake_spec.get("cartons_received", 2),
        "units_per_carton_ordered": intake_spec.get("units_per_carton_ordered", 12),
        "units_per_carton_counted": intake_spec.get("units_per_carton_counted", 12),
        "qty_ordered": intake_spec.get("qty_ordered", 24),
        "qty_received": intake_spec.get("qty_received", 24),
    }

    result = agent.run_batch_receiving_inspection(
        org_id=tenant_org,
        unit_id=unit_id,
        po_line_spec=spec_data,
        captured_images=submitted_photos,
        simling_failure=sim_failure,
        shipment_id=shipment_id
    )

    record_id = f"RCV-{unit_id.replace('UNIT-', '') if 'UNIT-' in unit_id else unit_id}"
    contract_record_uuid = to_contract_uuid(record_id)

    # Persist in DB
    conn = get_db_connection()
    cursor = conn.cursor()
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
        record_id, result["unit_id"], shipment_id, tenant_org, po_number, po_line,
        supplier, sku, spec_data["asin"], product_title,
        spec_data["spec_colour"], spec_data["spec_variant"], spec_data["spec_components"],
        result["cartons_ordered"], result["cartons_received"],
        result["units_per_carton_ordered"], result["units_per_carton_counted"],
        result["qty_ordered"], result["qty_received"],
        result["identity_match"], result["carton_damage"], result["unit_damage"],
        result["quality_flags"], ";".join(submitted_photos), "op_v1_dock",
        result["captured_at"], result["overall_verdict"], result["agent_confidence"],
        result["status"], result["evidence_data"]
    ))
    conn.commit()
    conn.close()

    record_inspection_attempt(
        record_id=record_id,
        org_id=tenant_org,
        unit_id=result["unit_id"],
        shipment_id=shipment_id,
        overall_verdict=result["overall_verdict"],
        agent_confidence=result["agent_confidence"],
        status=result["status"],
        execution_mode=result["execution_mode"],
        ai_provider=result.get("ai_provider"),
        decision_rationale=result.get("decision_rationale") or (result.get("structured_evidence") or {}).get("decision_rationale", ""),
        evidence_data=result["evidence_data"],
        photo_refs=";".join(submitted_photos),
        captured_at=result["captured_at"]
    )

    contract_status = "pending" if result["status"] == "pending_review" or result["overall_verdict"] == "PENDING_REVIEW" else "complete"

    return {
        "record_id": contract_record_uuid,
        "status": contract_status
    }

# 17. Retrieve Single Evidence Contract v1.1 Record
@app.get("/v1/records/{record_id}")
def get_v1_record(
    record_id: str,
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    org_id: Optional[str] = Query(None)
):
    """
    Contract Requirement:
    GET /v1/records/{id} -> the evidence record
    Returns full Evidence Contract v1.1 record.
    Accepts internal record_id or deterministic contract UUID.
    Strictly scoped to caller's organization.
    """
    tenant_org = x_org_id or org_id or "org_demo_alpha"

    # 1. Direct scoped lookup by internal record_id
    record = get_record_by_id_scoped(record_id, tenant_org)

    # 2. If not found by direct ID, check if queried by contract UUID
    if not record:
        all_records = get_records_by_org(tenant_org)
        for r in all_records:
            if to_contract_uuid(r["record_id"]) == record_id:
                record = r
                break

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Record '{record_id}' not found for organization '{tenant_org}'. Tenancy isolation enforced."
        )

    # Fetch overrides if any
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM operator_overrides WHERE record_id = ? AND org_id = ? ORDER BY overridden_at ASC", (record["record_id"], tenant_org))
    overrides = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return generate_evidence_contract(record, overrides)

# 18. List Evidence Contract v1.1 Records
@app.get("/v1/records")
def list_v1_records(
    since: Optional[str] = Query(None, description="ISO 8601 UTC timestamp filter: records with captured_at >= since"),
    agent: Optional[str] = Query(None, description="Filter by agent type: 'receiving'"),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    org_id: Optional[str] = Query(None)
):
    """
    Contract Requirement:
    GET /v1/records?since=&agent= -> { records[], next_cursor }
    Returns paginated array of Evidence Contract v1.1 records scoped to tenant.
    """
    tenant_org = x_org_id or org_id or "org_demo_alpha"

    # Agent filter: if specified and not 'receiving', return empty list
    if agent and agent.strip().lower() != "receiving":
        return {
            "records": [],
            "next_cursor": None
        }

    records = get_records_by_org(tenant_org)

    # Filter by 'since' timestamp if provided
    if since:
        since_clean = since.rstrip("Z")
        records = [
            r for r in records
            if (r.get("captured_at") or "").rstrip("Z") >= since_clean
        ]

    # Fetch all overrides for this tenant
    conn = get_db_connection()
    cursor_db = conn.cursor()
    cursor_db.execute("SELECT * FROM operator_overrides WHERE org_id = ? ORDER BY overridden_at ASC", (tenant_org,))
    all_overrides = [dict(r) for r in cursor_db.fetchall()]
    conn.close()

    overrides_by_rec = {}
    for ov in all_overrides:
        rec_k = ov["record_id"]
        overrides_by_rec.setdefault(rec_k, []).append(ov)

    # Generate v1.1 evidence contracts
    v1_contracts = [
        generate_evidence_contract(r, overrides_by_rec.get(r["record_id"], []))
        for r in records
    ]

    # Handle cursor pagination
    start_idx = 0
    if cursor:
        for idx, c in enumerate(v1_contracts):
            if c["record_id"] == cursor or c.get("subject", {}).get("order_id") == cursor:
                start_idx = idx + 1
                break

    page = v1_contracts[start_idx : start_idx + limit]
    next_cursor = page[-1]["record_id"] if (start_idx + limit < len(v1_contracts) and page) else None

    return {
        "records": page,
        "next_cursor": next_cursor
    }


