from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _evidence(check_type: str, observation, suffix: str) -> dict:
    return {
        "evidence_id": f"EVD-{suffix}",
        "image_id": "IMG-1",
        "check_type": check_type,
        "observation": observation,
        "confidence": 0.95,
        "description": f"Observed {check_type}.",
    }


def _request(evidence: list[dict] | None = None) -> dict:
    return {
        "request_id": "req-endpoint-001",
        "agent": "receiving-manager",
        "action": "verify_receiving",
        "payload": {
            "purchase_order": {
                "po_id": "PO-4001",
                "sku": "SKU-1",
                "product_name": "Sample item",
                "expected_quantity": 2,
                "variant": "Blue",
                "units_per_carton": 2,
                "expected_cartons": 1,
                "expected_components": ["cap"],
            },
            "shipment": {"shipment_id": "SHIP-1"},
            "evidence": evidence
            if evidence is not None
            else [
                _evidence("sku", "SKU-1", "sku"),
                _evidence("quantity", 2, "quantity"),
                _evidence("carton", 1, "carton"),
                _evidence("variant", "Blue", "variant"),
                _evidence("damage", "none", "damage"),
                _evidence("components", ["cap"], "components"),
            ],
        },
    }


def test_successful_pass_result_and_request_id_preservation():
    payload = _request()
    response = client.post("/api/v1/agent/receiving", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["request_id"] == payload["request_id"]
    assert result["status"] == "success"
    assert result["result"]["decision"] == "PASS"
    assert len(result["result"]["checks"]) == 6
    assert result["result"]["next_action"] is None


def test_exception_result_recommends_recovery_manager():
    payload = _request()
    payload["payload"]["evidence"][1]["observation"] = 1

    response = client.post("/api/v1/agent/receiving", json=payload)

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["decision"] == "EXCEPTION"
    assert result["next_action"]["agent"] == "recovery-manager"
    assert result["next_action"]["priority"] == "high"


def test_damage_evidence_array_produces_exception():
    payload = _request()
    payload["payload"]["evidence"][4]["observation"] = ["crushing"]

    response = client.post("/api/v1/agent/receiving", json=payload)

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["decision"] == "EXCEPTION"
    assert next(check for check in result["checks"] if check["check_name"] == "damage_check")["status"] == "FAIL"


def test_uncertain_result_is_preserved():
    response = client.post(
        "/api/v1/agent/receiving",
        json=_request([_evidence("sku", "SKU-1", "sku")]),
    )

    assert response.status_code == 200
    assert response.json()["result"]["decision"] == "UNCERTAIN"


def test_missing_request_id_returns_structured_error():
    payload = _request()
    del payload["request_id"]

    response = client.post("/api/v1/agent/receiving", json=payload)

    assert response.status_code == 400
    assert response.json()["status"] == "failed"
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_wrong_agent_returns_structured_error():
    payload = _request()
    payload["agent"] = "another-agent"

    response = client.post("/api/v1/agent/receiving", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_AGENT"
    assert response.json()["request_id"] == payload["request_id"]


def test_unsupported_action_returns_structured_error():
    payload = _request()
    payload["action"] = "unknown_action"

    response = client.post("/api/v1/agent/receiving", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_ACTION"


def test_malformed_purchase_order_returns_structured_error():
    payload = _request()
    del payload["payload"]["purchase_order"]["sku"]

    response = client.post("/api/v1/agent/receiving", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PURCHASE_ORDER"


def test_malformed_evidence_returns_structured_error():
    payload = _request()
    payload["payload"]["evidence"][0]["confidence"] = 1.5

    response = client.post("/api/v1/agent/receiving", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ANALYSIS_FAILED"


def test_missing_payload_field_returns_structured_error():
    payload = _request()
    del payload["payload"]["shipment"]

    response = client.post("/api/v1/agent/receiving", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MISSING_PAYLOAD"


def test_missing_purchase_order_returns_missing_payload_error():
    payload = _request()
    del payload["payload"]["purchase_order"]

    response = client.post("/api/v1/agent/receiving", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MISSING_PAYLOAD"


def test_no_evidence_returns_structured_failure_without_fake_success():
    payload = _request([])

    response = client.post("/api/v1/agent/receiving", json=payload)

    assert response.status_code == 422
    assert response.json()["status"] == "failed"
    assert response.json()["request_id"] == payload["request_id"]
    assert response.json()["error"]["code"] == "NO_EVIDENCE"
    assert "result" not in response.json()


def test_analysis_failure_returns_structured_internal_error(monkeypatch):
    from backend.app.api import agent as agent_api

    def fail_processing(_request):
        raise RuntimeError("private diagnostic should not be returned")

    monkeypatch.setattr(agent_api.agent_service, "process", fail_processing)
    response = client.post("/api/v1/agent/receiving", json=_request())

    assert response.status_code == 500
    assert response.json()["status"] == "failed"
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private diagnostic" not in response.text


def test_capabilities_endpoint():
    response = client.get("/api/v1/agent/receiving/capabilities")

    assert response.status_code == 200
    assert response.json() == {
        "agent": "receiving-manager",
        "version": "1.0.0",
        "protocol_version": "1.0",
        "capabilities": [
            "shipment_verification",
            "sku_verification",
            "quantity_verification",
            "carton_verification",
            "variant_verification",
            "damage_detection",
            "component_verification",
        ],
        "actions": ["verify_receiving"],
    }


def test_agent_health_endpoint():
    response = client.get("/api/v1/agent/receiving/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "agent": "receiving-manager",
        "version": "1.0.0",
    }


def test_existing_health_endpoint_is_unchanged():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "receiving-manager"}
