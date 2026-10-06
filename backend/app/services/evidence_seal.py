from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from backend.app.core.config import get_settings
from backend.app.models.inspection import (
    EvidenceImageDigest,
    EvidenceOutcome,
    EvidenceSubject,
    Inspection,
    SealedEvidenceRecord,
    SealedInspectionCheck,
)


def canonical_content_hash(payload: dict) -> str:
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def inspection_state_hash(inspection: Inspection, decision: str) -> str:
    state = {
        "decision": decision,
        "checks": [check.model_dump(mode="json") for check in inspection.checks],
        "prep_hold": inspection.prep_hold,
    }
    return canonical_content_hash(state)


def has_prep_hold(inspection: Inspection) -> bool:
    return (
        inspection.status == "PENDING_REVIEW"
        or not inspection.checks
        or any(check.status in {"FAIL", "UNCERTAIN"} for check in inspection.checks)
    )


def build_sealed_evidence_record(inspection: Inspection) -> SealedEvidenceRecord:
    settings = get_settings()
    model_version = "demo" if settings.demo_mode else settings.ai_model
    image_digests = [
        EvidenceImageDigest(
            view=image.image_type,
            sha256_digest=hashlib.sha256(Path(image.image_path).read_bytes()).hexdigest(),
        )
        for image in inspection.images
    ]
    sealed_checks = [
        SealedInspectionCheck(
            check_key=check.check_name,
            verdict=check.status,
            observed_state=check.observed_value,
            reason_code=f"{check.check_name.upper()}_{check.status}",
            measurements={
                "expected": check.expected_value,
                "observed": check.observed_value,
            },
            model_version=model_version,
            rule_ids=[check.check_name],
        )
        for check in inspection.checks
    ]
    prep_hold = has_prep_hold(inspection)
    inspection.prep_hold = prep_hold
    disposition = {
        "PASS": "ACCEPT",
        "EXCEPTION": "EXCEPTION",
        "UNCERTAIN": "HOLD",
    }[inspection.final_decision]
    record = SealedEvidenceRecord(
        record_id=f"REC-{uuid4().hex.upper()}",
        schema_version="1.0",
        organization_id=inspection.organization_id,
        subject=EvidenceSubject(
            po_number=inspection.po.po_id,
            po_line=inspection.po.po_line,
            sku=inspection.po.sku,
            asin=inspection.po.asin,
        ),
        images=image_digests,
        checks=sealed_checks,
        outcome=EvidenceOutcome(
            decision=inspection.final_decision,
            disposition=disposition,
            prep_hold=prep_hold,
        ),
        overrides=inspection.overrides.copy(),
        status=inspection.status,
        content_hash="0" * 64,
    )
    content_hash = canonical_content_hash(record.model_dump(mode="json", exclude={"content_hash"}))
    return record.model_copy(update={"content_hash": content_hash})
