import pytest
from pydantic import ValidationError

from backend.app.models.agent_contract import AgentRequest, AgentResponse


def _valid_request() -> dict:
    return {
        "request_id": "req-contract-001",
        "agent": "receiving-manager",
        "action": "verify_receiving",
        "payload": {
            "purchase_order": {
                "po_id": "PO-3001",
                "sku": "SKU-1",
                "product_name": "Sample item",
                "expected_quantity": 2,
                "variant": "Blue",
                "units_per_carton": 2,
                "expected_cartons": 1,
            },
            "shipment": {},
            "evidence": [
                {
                    "evidence_id": "EVD-1",
                    "image_id": "IMG-1",
                    "check_type": "quantity",
                    "observation": 2,
                    "confidence": 0.9,
                    "description": "Two units are visible.",
                }
            ],
        },
    }


def test_valid_agent_request():
    request = AgentRequest.model_validate(_valid_request())

    assert request.request_id == "req-contract-001"
    assert request.payload.purchase_order.po_id == "PO-3001"
    assert request.payload.evidence[0].observation == 2


@pytest.mark.parametrize(
    "update",
    [
        {"request_id": None},
        {"request_id": ""},
        {"request_id": "   "},
    ],
)
def test_request_id_is_required_and_nonempty(update):
    payload = _valid_request()
    payload.update(update)

    with pytest.raises(ValidationError):
        AgentRequest.model_validate(payload)


def test_agent_request_forbids_extra_fields():
    payload = _valid_request()
    payload["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        AgentRequest.model_validate(payload)


def test_agent_response_supports_structured_failure():
    response = AgentResponse(
        request_id="req-contract-fail",
        status="failed",
        error={
            "code": "ANALYSIS_FAILED",
            "message": "Evidence could not be analyzed.",
            "retryable": False,
        },
    )

    assert response.error is not None
    assert response.error.code == "ANALYSIS_FAILED"
