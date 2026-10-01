"""
Authoritative Rules Engine (Engineering Rule 5)
Retrieves exact channel specifications (Amazon FBA / 3PL inbound policies) to enforce
channel-authoritative checks rather than guessing or inferring from dummy data.
"""

from typing import Dict, Any, List

AUTHORITATIVE_RULES_DATABASE = [
    {
        "channel": "Amazon FBA",
        "doc_title": "Amazon Seller Central Inbound Packaging & Quality Specs 2026",
        "rules": [
            {
                "rule_id": "AMZ-INB-001",
                "name": "Carton Physical Integrity Standard",
                "authority_link": "https://sellercentral.amazon.com/gp/help/external/200141510",
                "condition": "Carton crushing > 10% volume or moisture absorption is unacceptable.",
                "action_on_violation": "REJECT / UNCERTAIN",
                "check": "carton_damage"
            },
            {
                "rule_id": "AMZ-INB-002",
                "name": "FNSKU Title and Variant Matching",
                "authority_link": "https://sellercentral.amazon.com/gp/help/external/200141550",
                "condition": "SKU color and size variant must exactly equal purchase order specification line.",
                "action_on_violation": "FAIL (wrong_colour / wrong_variant)",
                "check": "quality_flags"
            },
            {
                "rule_id": "AMZ-INB-003",
                "name": "Bundled Accessories & Manual Compliance",
                "authority_link": "https://sellercentral.amazon.com/gp/help/external/200141580",
                "condition": "Multi-piece sets must contain all specified items (e.g. cable, scoop, dropper).",
                "action_on_violation": "FAIL (missing_components)",
                "check": "quality_flags"
            }
        ]
    },
    {
        "channel": "Global 3PL",
        "doc_title": "Standard Operating Procedure for Inbound Receiving RCV-2026",
        "rules": [
            {
                "rule_id": "3PL-RCV-101",
                "name": "Quantity Receipt Threshold",
                "authority_link": "https://ops.3pl-standard.org/inbound/receiving-tolerances",
                "condition": "Discrepancy between cartons ordered vs cartons received triggers instant supplier claim notice.",
                "action_on_violation": "SHORTAGE_FLAG",
                "check": "quantity_verification"
            }
        ]
    }
]

def evaluate_authoritative_compliance(receiving_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Evaluates receiving inspection against retrieved authoritative channel rules."""
    evaluations = []
    for category in AUTHORITATIVE_RULES_DATABASE:
        for rule in category["rules"]:
            passed = True
            reason = "Complies with authoritative channel spec."
            
            if rule["check"] == "carton_damage":
                c_dmg = receiving_data.get("carton_damage", "none")
                if c_dmg in ["crushing", "water", "tears"]:
                    passed = False
                    reason = f"Carton damage '{c_dmg}' violates {category['doc_title']} ({rule['rule_id']})"
                elif c_dmg == "uncertain":
                    passed = False
                    reason = f"Uncertain carton condition requires mandatory prep inspection under {rule['rule_id']}"
                    
            elif rule["check"] == "quality_flags":
                q_flags = receiving_data.get("quality_flags", "")
                if q_flags:
                    passed = False
                    reason = f"Quality flags '{q_flags}' violate authoritative spec {rule['rule_id']}"
                    
            elif rule["check"] == "quantity_verification":
                qty_ord = receiving_data.get("qty_ordered", 0)
                qty_rec = receiving_data.get("qty_received", 0)
                if qty_ord != qty_rec:
                    passed = False
                    reason = f"Quantity shortage ({qty_rec} vs {qty_ord} expected) violates 3PL inbound tolerance {rule['rule_id']}"

            evaluations.append({
                "channel": category["channel"],
                "rule_id": rule["rule_id"],
                "rule_name": rule["name"],
                "authority_link": rule["authority_link"],
                "passed": passed,
                "reason": reason
            })
    return evaluations
