from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.app.models.agent_contract import (
    AgentCapabilities,
    AgentError,
    AgentErrorCode,
    AgentHealth,
    AgentRequest,
    AgentResponse,
)
from backend.app.services.agent_service import AgentProcessingError, ReceivingAgentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/agent/receiving", tags=["receiving-agent"])
agent_service = ReceivingAgentService()


def _request_id_from_body(body: Any) -> str:
    if isinstance(body, dict):
        request_id = body.get("request_id")
        if isinstance(request_id, str) and request_id.strip():
            return request_id
    return ""


def _error_response(
    request_id: str,
    code: AgentErrorCode,
    message: str,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
    status_code: int = 400,
) -> JSONResponse:
    response = AgentResponse(
        request_id=request_id,
        status="failed",
        error=AgentError(
            code=code,
            message=message,
            retryable=retryable,
            details=details,
        ),
    )
    return JSONResponse(status_code=status_code, content=_response_content(response))


def _response_content(response: AgentResponse) -> dict[str, Any]:
    content = response.model_dump(mode="json")
    return {key: value for key, value in content.items() if value is not None}


def _validation_error_code(error: ValidationError) -> tuple[AgentErrorCode, str]:
    first_error = error.errors(include_input=False)[0]
    first_location = first_error["loc"]
    if first_location and first_location[0] == "agent":
        return "INVALID_AGENT", "The request agent must be receiving-manager."
    if first_location and first_location[0] == "action":
        return "UNSUPPORTED_ACTION", "The requested action is not supported."
    if first_location and first_location[0] == "payload":
        if len(first_location) == 1:
            return "MISSING_PAYLOAD", "The payload is missing a required receiving field."
        if first_error["type"] == "missing" and len(first_location) == 2:
            return "MISSING_PAYLOAD", "The payload is missing a required receiving field."
        if len(first_location) > 1 and first_location[1] == "purchase_order":
            return "INVALID_PURCHASE_ORDER", "The purchase_order does not match the receiving contract."
        if len(first_location) > 1 and first_location[1] == "shipment":
            return "MISSING_PAYLOAD", "The shipment must be an object."
        return "ANALYSIS_FAILED", "The evidence does not match the receiving evidence contract."
    return "INVALID_REQUEST", "The request does not match the A2A contract."


@router.get("/capabilities", response_model=AgentCapabilities)
def get_capabilities() -> AgentCapabilities:
    return AgentCapabilities(
        capabilities=[
            "shipment_verification",
            "sku_verification",
            "quantity_verification",
            "carton_verification",
            "variant_verification",
            "damage_detection",
            "component_verification",
        ],
        actions=["verify_receiving"],
    )


@router.get("/health", response_model=AgentHealth)
def get_agent_health() -> AgentHealth:
    return AgentHealth()


@router.post("", response_model=AgentResponse)
async def receive_agent_request(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        logger.info("[REQ:] receiving-manager rejected invalid JSON")
        return _error_response("", "INVALID_REQUEST", "The request body must contain valid JSON.")

    request_id = _request_id_from_body(body)
    logger.info("[REQ:%s] receiving-manager started", request_id)

    try:
        agent_request = AgentRequest.model_validate(body)
    except ValidationError as exc:
        code, message = _validation_error_code(exc)
        logger.info("[REQ:%s] receiving-manager failed code=%s", request_id, code)
        details = {"field": ".".join(str(part) for part in exc.errors(include_input=False)[0]["loc"])}
        return _error_response(request_id, code, message, details=details)
    request_id = agent_request.request_id
    request_id = agent_request.request_id
    logger.info("[REQ:%s] action=%s", request_id, agent_request.action)

    try:
        result = agent_service.process(agent_request)
    except AgentProcessingError as exc:
        logger.info("[REQ:%s] receiving-manager failed code=%s", request_id, exc.code)
        return _error_response(
            request_id,
            exc.code,
            exc.message,
            retryable=exc.retryable,
            details=exc.details,
            status_code=422,
        )
    except TimeoutError:
        logger.warning("[REQ:%s] receiving-manager failed code=VISION_TIMEOUT", request_id)
        return _error_response(
            request_id,
            "VISION_TIMEOUT",
            "Vision analysis timed out; retrying may succeed.",
            retryable=True,
            status_code=504,
        )
    except Exception:
        logger.error("[REQ:%s] receiving-manager failed code=INTERNAL_ERROR", request_id)
        return _error_response(
            request_id,
            "INTERNAL_ERROR",
            "Receiving analysis could not be completed.",
            status_code=500,
        )

    logger.info("[REQ:%s] decision=%s", request_id, result["decision"])
    logger.info("[REQ:%s] receiving-manager completed", request_id)
    try:
        response = AgentResponse(
            request_id=request_id,
            status="success",
            result=result,
            metadata={"protocol_version": "1.0"},
        )
    except ValidationError:
        logger.error("[REQ:%s] receiving-manager failed code=INTERNAL_ERROR", request_id)
        return _error_response(
            request_id,
            "INTERNAL_ERROR",
            "Receiving analysis could not be completed.",
            status_code=500,
        )
    return JSONResponse(status_code=200, content=_response_content(response))
