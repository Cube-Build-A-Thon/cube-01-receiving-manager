import json
import sys
from types import SimpleNamespace

import pytest

import backend.app.services.vision as vision_module
from backend.app.core.config import Settings
from backend.app.models.inspection import Inspection, ReceivingImage
from backend.app.models.po import PurchaseOrder
from backend.app.services.vision import VisionAnalysisResponse, VisionImageResult, VisionService


def _inspection(image_ids, tmp_path):
    images = []
    for image_id in image_ids:
        image_path = tmp_path / f"{image_id}.png"
        image_path.write_bytes(b"sample image bytes")
        images.append(
            ReceivingImage(
                image_id=image_id,
                inspection_id="INS-TEST",
                filename=f"{image_id}.png",
                stored_filename=f"{image_id}.png",
                image_path=str(image_path),
                mime_type="image/png",
            )
        )
    return Inspection(
        inspection_id="INS-TEST",
        po=PurchaseOrder(
            po_id="PO-TEST",
            sku="SECRET-EXPECTED-SKU",
            product_name="Test product",
            expected_quantity=987654,
            variant="Expected blue",
            units_per_carton=12,
            expected_cartons=2,
            expected_components=["cap"],
        ),
        images=images,
    )


def _output(image_ids):
    return {
        "images": [
            {"image_id": image_id, "visibility": "clear", "observations": []}
            for image_id in image_ids
        ]
    }


def test_responses_api_uses_strict_text_json_schema_and_blind_prompt(monkeypatch, tmp_path):
    inspection = _inspection(["IMG-1", "IMG-2"], tmp_path)
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text=json.dumps(_output(["IMG-1", "IMG-2"])))

    def openai_client(**kwargs):
        return SimpleNamespace(responses=SimpleNamespace(create=create))

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=openai_client))
    monkeypatch.setattr(vision_module, "get_settings", lambda: Settings(api_key="test-key"))

    VisionService(inspection).analyze()

    assert "response_format" not in captured
    output_format = captured["text"]["format"]
    assert output_format["type"] == "json_schema"
    assert output_format["strict"] is True
    schema = output_format["schema"]
    image_schema = schema["properties"]["images"]["items"]
    assert image_schema["required"] == ["image_id", "visibility", "observations"]
    observation_schema = image_schema["properties"]["observations"]["items"]
    assert observation_schema["required"] == ["check_type", "observation", "confidence", "description"]
    prompt = captured["input"][0]["content"][0]["text"]
    assert "IMG-1" in prompt and "IMG-2" in prompt
    assert "SECRET-EXPECTED-SKU" not in prompt
    assert "987654" not in prompt
    assert sum(part["type"] == "input_image" for part in captured["input"][0]["content"]) == 2


def test_ai_response_must_reference_each_uploaded_image_once(tmp_path):
    service = VisionService(_inspection(["IMG-1", "IMG-2"], tmp_path))
    payload = VisionAnalysisResponse(
        images=[VisionImageResult(image_id="IMG-1", visibility="clear", observations=[])]
    )

    with pytest.raises(ValueError, match="every uploaded image exactly once"):
        service._validate_payload(payload, require_all_images=True)


def test_ai_output_missing_required_observation_is_rejected(monkeypatch, tmp_path):
    inspection = _inspection(["IMG-1", "IMG-2"], tmp_path)
    invalid_output = {
        "images": [
            {
                "image_id": image_id,
                "visibility": "clear",
                "observations": [
                    {"check_type": "quantity", "confidence": 0.9, "description": "Visible count."}
                ],
            }
            for image_id in ("IMG-1", "IMG-2")
        ]
    }

    def create(**_kwargs):
        return SimpleNamespace(output_text=json.dumps(invalid_output))

    def openai_client(**_kwargs):
        return SimpleNamespace(responses=SimpleNamespace(create=create))

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=openai_client))
    monkeypatch.setattr(vision_module, "get_settings", lambda: Settings(api_key="test-key"))

    with pytest.raises(ValueError, match="malformed structured output"):
        VisionService(inspection).analyze()


def test_demo_mode_uses_every_uploaded_server_image_id(monkeypatch, tmp_path):
    inspection = _inspection(["IMG-1", "IMG-2"], tmp_path)
    monkeypatch.setattr(vision_module, "get_settings", lambda: Settings(demo_mode=True))

    result = VisionService(inspection).analyze(scenario="correct_shipment")

    evidence_image_ids = {item["image_id"] for item in result["evidence"]}
    assert evidence_image_ids == {"IMG-1", "IMG-2"}
