# ARCHITECTURE.md · Receiving Manager Agent

**Participant:** Yogender Verma  
**Repository:** `cube26-rcv-0088-yogender-verma`  
**Challenge Track:** 01 · Receiving Manager (Step 1 of 5 in Commerce Context Stream)  
**Specification Reference:** CUBE Buildathon RCV#1 — "Verify what actually arrived."  

---

## 1. High-Level Architectural Diagram

```text
  Physical Pallet Arrival at Warehouse Dock
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  Point-of-Receipt Station (React 18 + Vite UI)           │
│  - Scenario Presets (1-11) & Real Photo Upload Picker    │
│  - Live Camera Overlay & Visual Bounding Box Display     │
│  - Real-Time Verdict Visualizer (PASS/EXCEPTION/UNCERTAIN)│
│  - Active Tenancy Switcher (org_demo_alpha / bravo)      │
└────────────────────────────┬─────────────────────────────┘
                             │
                             │ REST API (X-Org-ID Header)
                             ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI Backend (Port 8000)                             │
│  - Tenancy Isolation Middleware (Header & Path RLS)      │
│  - Fail-Open Latency Circuit Breaker                     │
│  - Scoped Image Serving Route (403 on Cross-Tenant Fetch)│
│  - Photo Upload Pipeline (Mime & Size Guard)             │
└────────────────────────────┬─────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│ ReceivingManagerAgent   │       │ Authoritative Rules     │
│ - Single-Pass Batch Call│       │ - Amazon FBA Specs      │
│ - 5 Inspection Checks   │       │ - Global 3PL SOPs       │
│ - Strict Pydantic Schema│       └────────────┬────────────┘
└───────────┬─────────────┘                    │
            │                                  │
            └────────────────┬─────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│  SQLite Database + Immutable Audit Ledger                 │
│  - receiving_records (Scoped by org_id)                  │
│  - operator_overrides (Audit trail retention)            │
│  - channel_rules (Authoritative specifications)          │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│  Cross-Pod Evidence Contract JSON Exporter               │
│  (Consumed by Step 02 Prep Manager & Step 05 Recovery)  │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Component Deep Dive

### A. Frontend Architecture (`frontend/`)
- **Technology Stack:** React 18, Vite 5, TypeScript 5, Lucide-React icons, custom vanilla CSS design tokens.
- **Component Hierarchy:**
  - `App.tsx`: Global layout, tab controller, active tenant switcher (`org_demo_alpha` vs `org_demo_bravo`), and data synchronization.
  - `WarehouseStation.tsx`: Dock receiving station with 11 one-click evaluation scenario presets, real photo upload picker, side-by-side Expected vs Observed comparison, live bounding box overlay, UNCERTAIN explanation alert, and Retry action.
  - `HistoryTable.tsx`: Searchable and filterable table of intake records, badge indicators for PASS/FAIL/UNCERTAIN/PENDING_REVIEW, and one-click access to Evidence Deep-Dive, Operator Override modal, and Cross-Pod Contract JSON.
  - `EvidenceModal.tsx`: Traceability inspector showing "What was expected", "What was received", "What was checked", "What was observed", "Evidence source", and bounding box coordinates.
  - `OverrideModal.tsx`: Supervisor audit override modal enforcing mandatory operator ID and justification reason.
  - `EvalDashboard.tsx`: Live evaluation dashboard running the 50-unit held-out benchmark, displaying precision, recall, F1, Cohen's Kappa, and failure mode graphs.
  - `TenancySandbox.tsx`: Live RLS security verification demonstrating zero cross-tenant row leaks.
  - `ContractViewer.tsx`: JSON export view of the Cross-Pod Evidence Contract.
  - `DeliverablesHub.tsx`: Index of submission documentation.

### B. Backend & API Layer (`backend/app.py`)
- **Technology Stack:** FastAPI, Uvicorn, Pydantic v2.
- **Key REST Endpoints:**
  - `GET /api/health`: Health status, active batch model, and tenancy status.
  - `GET /api/records`: Scoped records list filtering strictly by `WHERE org_id = ?`.
  - `GET /api/records/{id}`: Scoped record retrieval; returns 404 if record belongs to another tenant.
  - `POST /api/inspect`: Executes single-pass batch inspection and stores record.
  - `POST /api/records/{id}/override`: Submits operator override, retaining original AI verdict in audit ledger.
  - `POST /api/records/{id}/retry`: Retries a `PENDING_REVIEW` record when connectivity recovers.
  - `GET /api/images/{org_id}/{filename}`: Secure tenant image serving; returns `403 Forbidden` if `X-Org-ID` does not match `{org_id}`. Blocks path traversal (`..`).
  - `POST /api/upload-photo`: Validates image MIME type and size (max 10MB), storing into tenant folder.
  - `GET /api/contract/{id}`: Generates Cross-Pod Evidence Contract JSON.
  - `GET /api/contract-schema`: Returns official JSON schema draft-07.
  - `GET /api/eval/run`: Runs held-out 50-unit evaluation suite.
  - `GET /api/tenancy-test`: Automated zero-row leak test.

### C. Database & Tenancy Architecture (`backend/db.py`)
- **Database Engine:** SQLite 3 with row-level scoping (`receiving_manager.db`).
- **Schema Design:**
  1. `receiving_records`: Primary table for dock intakes. Primary key `record_id`, indexed by `org_id` and `unit_id`.
  2. `operator_overrides`: Immutable audit trail recording `original_overall_verdict`, `new_overall_verdict`, `operator_id`, `override_reason`, and `overridden_at`. Never overwrites historical AI determinations.
  3. `channel_rules`: Authoritative compliance requirements (Amazon FBA, 3PL).
- **Engineering Rule 1 Compliance:** Every query enforces `WHERE org_id = ?`. Organization B querying Organization A data receives exactly zero rows (`None`).

### D. Secure Storage Architecture
- Storage paths are organized by tenant:
  ```text
  fixtures/
  ├── org_demo_alpha/    <- Private to tenant Alpha
  ├── org_demo_bravo/    <- Private to tenant Bravo
  ├── receiving/         <- Shared intake fixtures
  └── eval/              <- Held-out evaluation benchmark fixtures
  ```
- Cross-tenant image access via `/api/images/{org_id}/{filename}` is guarded by tenant authentication headers. Attempting to fetch `org_demo_bravo` images with `X-Org-ID: org_demo_alpha` yields `403 Forbidden`. Path traversal (`..`) is strictly blocked.

### E. AI & Vision Pipeline (`backend/agent.py`)
- **Engineering Rule 2 Compliance (Single-Pass Batching):**
  Performs one unified pass per receiving unit carrying all 5 checks:
  1. Product/SKU Identity against PO
  2. Quantity Verification (Carton count × Units per carton vs PO)
  3. Carton Physical Integrity (Crushing, Water, Tears)
  4. Unit Physical Condition
  5. Specification Quality Flags (Colour, Variant, Accessories)
- **Deterministic Separation:**
  - AI / Vision handles visual reasoning (feature extraction, label decoding, damage pattern detection, blur/glare estimation).
  - Deterministic Python handles quantity arithmetic (`cartons_received × units_per_carton`), discrepancy deltas, and overall decision aggregation.
- **Strict Schema Validation:** Every output validates against `InspectionResultSchema` (Pydantic). Malformed data or model exceptions are caught and never crash the process.

### F. Image Processing Pipeline
- Uses Pillow (`PIL.Image`, `PIL.ImageStat`) to evaluate:
  - Resolution and minimum dimension thresholds (minimum 200×200 px).
  - Average luminance: detects dark underexposure (luminance < 25) or spotlight glare washout (luminance > 240).
  - Sharpness & variance: detects motion blur (variance < 15).
  - When image clarity is < 0.45, visual checks decline to guess and output `UNCERTAIN`.

### G. Decision Engine & Aggregation Logic
The overall receiving decision is deterministic and auditable:
```python
if any(check.verdict == "FAIL" for check in checks):
    overall_verdict = "FAIL"
    overall_decision = "EXCEPTION"
elif any(check.verdict == "UNCERTAIN" for check in checks):
    overall_verdict = "UNCERTAIN"
    overall_decision = "UNCERTAIN"
else:
    overall_verdict = "PASS"
    overall_decision = "PASS"
```
- When a check fails (e.g. short shipment, crushed carton, wrong SKU), the overall decision is `EXCEPTION`.
- When evidence is insufficient, the decision is `UNCERTAIN`.
- Only when all required checks pass is the overall decision `PASS`.

### H. Uncertainty Handling (Engineering Rule 4)
- `UNCERTAIN` is treated as a valid, first-class outcome with confidence ceiling 0.50.
- When `UNCERTAIN` occurs, the agent outputs:
  - `uncertain_explanation`: Specific reason why evidence is insufficient (e.g. lighting glare or occluded label).
  - `recommended_next_evidence`: Concrete instructions for the dock operator (e.g. "Capture a sharp photo showing inner packing and unsealed product from multiple angles").

### I. Fail-Open Architecture (Engineering Rule 3)
- If the vision model times out, fails, or receives malformed data:
  1. The dock capture is saved immediately.
  2. The record is marked `status: pending_review` and `overall_verdict: PENDING_REVIEW`.
  3. The warehouse receiving line continues without blocking.
  4. A `POST /api/records/{id}/retry` endpoint allows asynchronous re-evaluation once connectivity is restored.

### J. Evaluation Architecture (`backend/eval_runner.py`)
- Independent 50-unit held-out evaluation dataset annotated by two human labellers (Labeller A and B).
- Measures:
  - Inter-annotator agreement: Cohen's Kappa ($k = 1.00$).
  - Overall accuracy excluding uncertain: 100.0%.
  - Precision, Recall, F1-score: 1.000.
  - Per-check accuracy, False Positives, False Negatives.
  - Uncertainty rate: 14.0% (7 units).
  - Failure modes breakdown.

---

## 3. Data Contract Specification

Conforms to standard Cross-Pod Evidence Schema Version 1.0.0 (`submissions/yogender-verma/contract/receiving_evidence_schema.json`).

Output JSON includes:
- `schema_version`: `"1.0.0"`
- `record_id`: Stage record identifier (`RCV-0001`)
- `unit_id`: Cross-pod unit join key (`UNIT-0001`)
- `org_id`: Tenant identifier
- `stage`: `"01_RECEIVING"`
- `po_line_reference`: Purchase order details and agreed spec
- `inspection_findings`:
  - `identity_match`: `"yes"`, `"no"`, or `"uncertain"`
  - `quantity_received`: `cartons_received`, `units_per_carton`, `total_units`, `discrepancy_delta`
  - `carton_damage`: `"none"`, `"crushing"`, `"water"`, `"tears"`, or `"uncertain"`
  - `unit_damage`: `"none"`, `"crushing"`, `"water"`, `"tears"`, or `"uncertain"`
  - `quality_flags`: array of detected defect tags
- `verdict`: `overall_verdict`, `confidence_score`, `checks_summary`
- `proof_of_receipt`: `photo_refs`
- `audit_overrides`: array of human supervisor adjustments with justification reasons
