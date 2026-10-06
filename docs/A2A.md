# Round 3 A2A Integration

The Receiving Manager exposes a versioned agent API for the Pod orchestrator. The API accepts a receiving-verification request and returns the Receiving Manager's own deterministic decision and supporting checks. It does not invoke another agent.

## Ownership and routing

The Receiving Manager owns purchase-order validation, evidence interpretation, receiving checks, and the final `PASS`, `EXCEPTION`, or `UNCERTAIN` decision. Evidence in an A2A request represents observations already available to the receiving agent; it is validated and evaluated with the existing VisionService check builder and deterministic decision engine.

The Pod orchestrator owns selecting and sequencing agents, cross-agent routing, retries, timeouts, and the final multi-agent response. When a material exception is found, the Receiving Manager includes a `next_action` recommendation for `recovery-manager`; the orchestrator decides whether and how to route it.

## Identity and version

- Agent identity: `receiving-manager`
- Agent version: `1.0.0`
- Protocol version: `1.0`
- Supported action: `verify_receiving`

## Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/agent/receiving/health` | Agent health and version |
| `GET` | `/api/v1/agent/receiving/capabilities` | Supported capabilities and actions |
| `POST` | `/api/v1/agent/receiving` | Verify shipment evidence |

The existing `/api/inspections` workflow and `/api/health` endpoint remain separate and unchanged.

## Request format

The request object rejects additional top-level properties. `payload` requires `purchase_order`, `shipment`, and `evidence`. The purchase order uses the existing Receiving Manager purchase-order model. Evidence items carry an image reference, supported check type, observed value, confidence, and description.

```json
{
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
      "expected_components": ["cap"]
    },
    "shipment": {"shipment_id": "SHIP-1"},
    "evidence": [
      {
        "evidence_id": "EVD-sku",
        "image_id": "IMG-1",
        "check_type": "sku",
        "observation": "SKU-1",
        "confidence": 0.95,
        "description": "Observed sku."
      },
      {
        "evidence_id": "EVD-quantity",
        "image_id": "IMG-1",
        "check_type": "quantity",
        "observation": 2,
        "confidence": 0.95,
        "description": "Observed quantity."
      },
      {
        "evidence_id": "EVD-carton",
        "image_id": "IMG-1",
        "check_type": "carton",
        "observation": 1,
        "confidence": 0.95,
        "description": "Observed carton."
      },
      {
        "evidence_id": "EVD-variant",
        "image_id": "IMG-1",
        "check_type": "variant",
        "observation": "Blue",
        "confidence": 0.95,
        "description": "Observed variant."
      },
      {
        "evidence_id": "EVD-damage",
        "image_id": "IMG-1",
        "check_type": "damage",
        "observation": "none",
        "confidence": 0.95,
        "description": "Observed damage."
      },
      {
        "evidence_id": "EVD-components",
        "image_id": "IMG-1",
        "check_type": "components",
        "observation": ["cap"],
        "confidence": 0.95,
        "description": "Observed components."
      }
    ]
  },
  "metadata": {"trace_id": "trace-001"}
}
```

Supported evidence `check_type` values are `sku`, `quantity`, `variant`, `damage`, `components`, and `carton`. Observations may be strings, integers, lists of strings, or `null`. At least one evidence item is required; no observations or shipment facts are invented by this endpoint.

## Response format

Successful processing returns `status: "success"` and a result with the deterministic decision, structured checks, supplied evidence, derived observations/findings, and an optional downstream recommendation. This passing example uses a compact PO and corresponding evidence:

```json
{
  "request_id": "req-endpoint-001",
  "agent": "receiving-manager",
  "status": "success",
  "result": {
    "po_id": "PO-4001",
    "decision": "PASS",
    "checks": [
      {
        "check_name": "sku_check",
        "status": "PASS",
        "expected_value": "SKU-1",
        "observed_value": "SKU-1",
        "evidence_ids": [],
        "reason": "Observed SKU matches the expected SKU.",
        "confidence": 0.95
      },
      {
        "check_name": "quantity_check",
        "status": "PASS",
        "expected_value": 2,
        "observed_value": 2,
        "evidence_ids": [],
        "reason": "Observed quantity matches the expected quantity.",
        "confidence": 0.95
      },
      {
        "check_name": "carton_check",
        "status": "PASS",
        "expected_value": 1,
        "observed_value": 1,
        "evidence_ids": [],
        "reason": "Observed carton count matches the expected carton count.",
        "confidence": 0.95
      },
      {
        "check_name": "variant_check",
        "status": "PASS",
        "expected_value": "Blue",
        "observed_value": "Blue",
        "evidence_ids": [],
        "reason": "Observed variant matches the expected variant.",
        "confidence": 0.95
      },
      {
        "check_name": "damage_check",
        "status": "PASS",
        "expected_value": "none",
        "observed_value": ["none"],
        "evidence_ids": [],
        "reason": "No visible damage was detected.",
        "confidence": 0.95
      },
      {
        "check_name": "component_check",
        "status": "PASS",
        "expected_value": ["cap"],
        "observed_value": ["cap"],
        "evidence_ids": [],
        "reason": "All expected components are present.",
        "confidence": 0.95
      }
    ],
    "evidence": [
      {
        "evidence_id": "EVD-sku",
        "image_id": "IMG-1",
        "check_type": "sku",
        "observation": "SKU-1",
        "confidence": 0.95,
        "description": "Observed sku.",
        "bounding_region": null
      },
      {
        "evidence_id": "EVD-quantity",
        "image_id": "IMG-1",
        "check_type": "quantity",
        "observation": 2,
        "confidence": 0.95,
        "description": "Observed quantity.",
        "bounding_region": null
      },
      {
        "evidence_id": "EVD-carton",
        "image_id": "IMG-1",
        "check_type": "carton",
        "observation": 1,
        "confidence": 0.95,
        "description": "Observed carton.",
        "bounding_region": null
      },
      {
        "evidence_id": "EVD-variant",
        "image_id": "IMG-1",
        "check_type": "variant",
        "observation": "Blue",
        "confidence": 0.95,
        "description": "Observed variant.",
        "bounding_region": null
      },
      {
        "evidence_id": "EVD-damage",
        "image_id": "IMG-1",
        "check_type": "damage",
        "observation": "none",
        "confidence": 0.95,
        "description": "Observed damage.",
        "bounding_region": null
      },
      {
        "evidence_id": "EVD-components",
        "image_id": "IMG-1",
        "check_type": "components",
        "observation": ["cap"],
        "confidence": 0.95,
        "description": "Observed components.",
        "bounding_region": null
      }
    ],
    "observations": [
      {
        "detected_sku": "SKU-1",
        "detected_product_name": null,
        "observed_quantity": 2,
        "observed_cartons": null,
        "observed_units_per_carton": null,
        "detected_variant": "Blue",
        "damage_types": [],
        "missing_components": [],
        "visibility_quality": "uncertain",
        "confidence": 0.95
      }
    ],
    "findings": [],
    "next_action": null
  },
  "metadata": {"protocol_version": "1.0"}
}
```

When the deterministic decision is `EXCEPTION`, `next_action` recommends recovery routing, for example:

```json
{
  "agent": "recovery-manager",
  "reason": "Quantity mismatch: expected 24, observed 22.",
  "priority": "high"
}
```

## Error format and failure behavior

Failures use `status: "failed"` and a structured `error` object. They never include a success-shaped or fabricated result.

```json
{
  "request_id": "req-001",
  "agent": "receiving-manager",
  "status": "failed",
  "error": {
    "code": "NO_EVIDENCE",
    "message": "At least one evidence item is required to verify a shipment.",
    "retryable": false
  }
}
```

Error codes are `INVALID_REQUEST`, `INVALID_AGENT`, `UNSUPPORTED_ACTION`, `MISSING_PAYLOAD`, `INVALID_PURCHASE_ORDER`, `NO_EVIDENCE`, `ANALYSIS_FAILED`, `VISION_TIMEOUT`, and `INTERNAL_ERROR`. Invalid contracts and missing evidence are not retryable. A vision timeout is retryable. Internal failures are marked non-retryable because retry safety cannot be established by the Receiving Manager. The orchestrator controls retry policy and timeouts.

Machine-readable request, response, error, and capability schemas are in `contracts/`.
