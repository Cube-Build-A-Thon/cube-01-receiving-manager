# Receiving Manager Architecture

## Overview

The app is a compact modular monolith that handles receiving-photo intake, optional computer vision analysis, evidence validation, and deterministic verdicting.

## Flow

```text
Frontend
  ↓
FastAPI
  ↓
Vision Service
  ↓
Evidence Validation
  ↓
Decision Engine
  ↓
Inspection Result
```

## Backend components

- `backend/app/main.py` exposes the FastAPI app and health endpoint.
- `backend/app/api/inspections.py` handles inspection creation, image upload, retrieval, and analyze.
- `backend/app/models/` defines the Pydantic contracts for PO data, images, evidence, checks, and inspection records.
- `backend/app/core/config.py` reads environment values for upload limits, AI settings, and demo mode.
- `backend/app/core/decision_engine.py` applies deterministic PASS / FAIL / UNCERTAIN comparison logic.
- `backend/app/services/storage.py` stores uploaded files under an inspection-scoped path.
- `backend/app/services/vision.py` orchestrates the multimodal AI contract and demo-mode responses.
- `backend/app/database/repository.py` manages the in-memory inspection store.

## Vision and AI flow

1. Receive inspection and uploaded images.
2. Validate that images exist and belong to the inspection.
3. If `DEMO_MODE=true`, return a controlled scenario response.
4. If `AI_API_KEY` is configured, call the OpenAI Responses API with PO context and image inputs.
5. Validate the model response against the structured schema.
6. Convert valid observations into evidence records tied to image IDs.
7. Compare expected and observed values in Python.
8. Record the result and return the inspection summary.

## Storage

Images are written into a safe inspection directory under the configured upload root. Filenames are sanitized and server-generated to block path traversal and keep the storage layer deterministic.

## Security

The upload path validates:

- supported image extensions
- MIME-type and file signature checks
- empty-file rejection
- oversized-file rejection
- path traversal prevention
- inspection-scoped file ownership checks

## Decision engine

All final decisions are computed by Python:

- `FAIL` in any required check => `EXCEPTION`
- otherwise `UNCERTAIN` if any check is uncertain
- otherwise `PASS`

The model is never allowed to make the final business decision.

## Frontend

The frontend is a simple dashboard for:

- creating a PO-based inspection
- uploading photos
- analyzing the inspection
- displaying evidence and check cards
- selecting demo scenarios when the app is running in demo mode

## Notes

This is a hackathon-ready modular monolith. It is intentionally simple enough to run locally while still preserving a clean separation of concerns.
