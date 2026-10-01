from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.config import get_settings
from backend.app.core.decision_engine import evaluate_overall
from backend.app.database.repository import InspectionRepository
from backend.app.models.inspection import Inspection, InspectionCheck, ReceivingImage
from backend.app.models.po import PurchaseOrder
from backend.app.services.storage import LocalStorage
from backend.app.services.vision import VisionService

router = APIRouter(prefix="/api/inspections", tags=["inspections"])
repository = InspectionRepository()
storage = LocalStorage(root_dir=get_settings().upload_root_dir)


class InspectionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    po: PurchaseOrder
    images: list[ReceivingImage] = Field(default_factory=list)


class InspectionOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)


def _build_agent_summary(inspection: Inspection) -> str:
    if not inspection.checks:
        return "The receiving agent has not produced a final evidence-based verdict yet."

    failed_checks = [check for check in inspection.checks if check.status == "FAIL"]
    uncertain_checks = [check for check in inspection.checks if check.status == "UNCERTAIN"]

    if inspection.final_decision == "PASS":
        return "The receiving agent verified the shipment against the PO and found no material deviations."

    if inspection.final_decision == "EXCEPTION":
        if failed_checks:
            names = ", ".join(check.check_name.replace("_check", "").replace("_", " ") for check in failed_checks[:3])
            return f"The receiving agent flagged the shipment as EXCEPTION because the following checks failed: {names}."
        return "The receiving agent flagged the shipment as EXCEPTION due to clear material evidence against the PO."

    if uncertain_checks:
        names = ", ".join(check.check_name.replace("_check", "").replace("_", " ") for check in uncertain_checks[:3])
        return f"The receiving agent marked the shipment as UNCERTAIN because the evidence is inconclusive in: {names}."

    return "The receiving agent completed the inspection and recorded a conservative outcome based on the visible evidence."


def _detect_image_mime(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid supported image.")


def _validate_image_upload(file: UploadFile, inspection_id: str):
    settings = get_settings()
    allowed_types = {item.strip().lower() for item in settings.allowed_image_types.split(",") if item.strip()}
    allowed_exts = {item.strip().lower() for item in settings.allowed_extensions.split(",") if item.strip()}

    original_name = (file.filename or "upload").strip()
    if not original_name or original_name in {".", ".."}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file name is invalid.")

    suffix = Path(original_name).suffix.lower()
    if suffix not in allowed_exts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported file extension: {suffix}.")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Image file is empty: {original_name}")

    max_bytes = settings.max_image_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Image exceeds the configured size limit.")

    detected_type = _detect_image_mime(content)
    if detected_type not in allowed_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image MIME type.")

    expected_by_suffix = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    if expected_by_suffix.get(suffix) != detected_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file content does not match the provided file extension.")

    if file.content_type and file.content_type.lower() not in allowed_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported file type: {file.content_type}")

    safe_stored_name = f"{uuid4().hex}_{inspection_id}{suffix}"
    return {
        "original_name": original_name,
        "stored_name": safe_stored_name,
        "mime_type": detected_type,
        "content": content,
    }


@router.get("")
def list_inspections():
    items = repository.list()
    return {"items": [inspection.model_dump(mode="json") for inspection in items], "count": len(items)}


@router.post("")
def create_inspection(payload: InspectionCreateRequest):
    try:
        inspection_id = repository.generate_id()
        inspection = Inspection(
            inspection_id=inspection_id,
            po=payload.po,
            images=payload.images,
            status="draft",
            final_decision="UNCERTAIN",
            checks=[],
            observations=[],
            evidence=[],
            agent_summary="The receiving agent is waiting for intake and evidence capture.",
        )
        repository.create(inspection)
        return inspection.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{inspection_id}")
def get_inspection(inspection_id: str):
    inspection = repository.get(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    return inspection.model_dump(mode="json")


@router.post("/{inspection_id}/images")
def upload_images(inspection_id: str, files: list[UploadFile] = File(...), image_type: str = Form("receiving_photo")):
    inspection = repository.get(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No image files were provided")

    settings = get_settings()
    if len(inspection.images) + len(files) > settings.upload_max_images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Maximum image count exceeded for this inspection ({settings.upload_max_images}).")

    saved_images: list[ReceivingImage] = []
    for file in files:
        validated = _validate_image_upload(file, inspection_id)
        storage_path = storage.save(inspection_id, validated["stored_name"], validated["content"])
        image_id = f"IMG-{uuid4().hex[:8].upper()}"
        saved_images.append(
            ReceivingImage(
                image_id=image_id,
                inspection_id=inspection_id,
                filename=validated["original_name"],
                stored_filename=validated["stored_name"],
                image_path=storage_path,
                image_type=image_type or "receiving_photo",
                mime_type=validated["mime_type"],
                file_size=len(validated["content"]),
                processing_state="uploaded",
                uploaded_at=datetime.now(timezone.utc),
            )
        )

    inspection.images.extend(saved_images)
    inspection.updated_at = datetime.now(timezone.utc)
    inspection.status = "draft" if inspection.status == "draft" else inspection.status
    repository.update(inspection)
    return {"inspection_id": inspection_id, "images": [image.model_dump(mode="json") for image in saved_images]}


@router.get("/{inspection_id}/images/{image_id}")
def get_inspection_image(inspection_id: str, image_id: str):
    inspection = repository.get(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    image_record = next((img for img in inspection.images if img.image_id == image_id), None)
    if image_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    try:
        file_path = storage.resolve(inspection_id, image_record.stored_filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image path") from exc

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file not found")

    return FileResponse(file_path, media_type=image_record.mime_type, filename=image_record.filename)


@router.post("/{inspection_id}/analyze")
def analyze_inspection(inspection_id: str, scenario: str | None = None):
    inspection = repository.get(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    settings = get_settings()
    if settings.demo_mode:
        try:
            result = VisionService(inspection).analyze(scenario=scenario)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        inspection.checks = [InspectionCheck.model_validate(item) for item in result["checks"]]
        inspection.evidence = []
        for evidence in result["evidence"]:
            inspection.evidence.append(__import__("backend.app.models.evidence", fromlist=["Evidence"]).Evidence.model_validate(evidence))
        inspection.observations = []
        for observation in result["observations"]:
            inspection.observations.append(__import__("backend.app.models.inspection", fromlist=["VisualObservation"]).VisualObservation.model_validate(observation))
        inspection.final_decision = result["decision"]
        inspection.override_decision = None
        inspection.override_reason = None
        inspection.agent_summary = _build_agent_summary(inspection)
        inspection.status = "completed"
        inspection.updated_at = datetime.now(timezone.utc)
        repository.update(inspection)
        return {
            "inspection_id": inspection_id,
            "decision": result["decision"],
            "checks": result["checks"],
            "evidence": result["evidence"],
            "observations": result["observations"],
            "demo_mode": True,
            "analysis_status": "demo",
            "agent_summary": inspection.agent_summary,
        }

    if not settings.api_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI analysis is not configured. Set AI_API_KEY or OPENAI_API_KEY in the environment.")
    if not inspection.images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No images uploaded for analysis")

    try:
        result = VisionService(inspection).analyze(scenario=scenario)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    inspection.checks = [InspectionCheck.model_validate(item) for item in result["checks"]]
    inspection.evidence = []
    for evidence in result["evidence"]:
        inspection.evidence.append(__import__("backend.app.models.evidence", fromlist=["Evidence"]).Evidence.model_validate(evidence))
    inspection.observations = []
    for observation in result["observations"]:
        inspection.observations.append(__import__("backend.app.models.inspection", fromlist=["VisualObservation"]).VisualObservation.model_validate(observation))
    inspection.final_decision = result["decision"]
    inspection.override_decision = None
    inspection.override_reason = None
    inspection.agent_summary = _build_agent_summary(inspection)
    inspection.status = "completed"
    inspection.updated_at = datetime.now(timezone.utc)
    repository.update(inspection)

    return {
        "inspection_id": inspection_id,
        "decision": result["decision"],
        "checks": result["checks"],
        "evidence": result["evidence"],
        "observations": result["observations"],
        "demo_mode": False,
        "analysis_status": "complete",
        "agent_summary": inspection.agent_summary,
    }


@router.post("/{inspection_id}/override")
def override_inspection(inspection_id: str, payload: InspectionOverrideRequest):
    inspection = repository.get(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    decision = payload.decision.strip().upper()
    if decision not in {"PASS", "EXCEPTION", "UNCERTAIN"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Override decision must be PASS, EXCEPTION, or UNCERTAIN.")

    inspection.override_decision = decision
    inspection.override_reason = payload.reason.strip()
    inspection.final_decision = decision
    inspection.status = "completed"
    inspection.updated_at = datetime.now(timezone.utc)
    inspection.agent_summary = (
        f"Operator override applied: {decision}. Reason: {inspection.override_reason}"
    )
    repository.update(inspection)

    return {
        "inspection_id": inspection_id,
        "override_decision": inspection.override_decision,
        "override_reason": inspection.override_reason,
        "final_decision": inspection.final_decision,
        "status": inspection.status,
        "agent_summary": inspection.agent_summary,
    }
