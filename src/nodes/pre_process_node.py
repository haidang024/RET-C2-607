"""PreProcessNode — normalize staff/kiosk request into a product recommendation query."""

from __future__ import annotations

import json
import re
from typing import Any, ClassVar

from framework.errors import SecurityViolationError
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

MAX_INPUT_CHARS = 2048

# Patterns that indicate individual customer identifiers — reject per APPI boundary
_CUSTOMER_ID_PATTERN = re.compile(
    r"\b(customer_id|user_id|member_id|card_no|顧客ID|会員番号|ポイントカード番号)\b",
    re.IGNORECASE,
)
_GREETING_ONLY = re.compile(
    r"^(?:hello|hi|hey|hello[,. ]*hi|xin chào|chào|こんにちは)[!. ,]*$",
    re.IGNORECASE,
)
_INPUT_GUIDANCE = [
    "Provide product_name or barcode using JSON or key:value lines.",
    'Example JSON: {"product_name": "green tea", "store_id": "STORE-001"}.',
    "Do not include customer IDs, member numbers, or stored personal profiles.",
]


def _input_error(message: str) -> dict[str, Any]:
    return {
        "status": AgentStatus.SUCCESS.value,
        "validated_input": "",
        "input_error_message": message,
        "input_error_guidance": _INPUT_GUIDANCE,
    }


class PreProcessNode(FunctionNode):
    """Validate and normalize the staff/kiosk product query.

    Outer graph boundary node. Runs at VERIFIED_EXTERNAL.
    Rejects individual customer identifiers per APPI aggregate-only boundary.
    Input may be JSON or colon-delimited key:value lines.
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def _extra_security_gate_input(self, state: dict[str, Any]) -> dict[str, Any]:
        user_input = state.get("user_input", "")
        if not isinstance(user_input, str):
            raise SecurityViolationError("PreProcessNode: user_input must be a plain string")
        if len(user_input) > MAX_INPUT_CHARS:
            raise SecurityViolationError(f"PreProcessNode: user_input exceeds {MAX_INPUT_CHARS} chars")
        if _CUSTOMER_ID_PATTERN.search(user_input):
            raise SecurityViolationError(
                "PreProcessNode: individual customer identifiers are not permitted (APPI boundary)"
            )
        return state

    def execute(self, state: dict) -> dict:
        raw = state.get("user_input", "") or ""
        if not raw.strip():
            return _input_error("No product recommendation request was provided.")

        if _GREETING_ONLY.fullmatch(raw.strip()):
            return _input_error("The message contains only a greeting and no product request.")

        parsed = _parse_request(raw)
        if parsed is None:
            return _input_error("The request could not be parsed as JSON or key:value lines.")

        product_name = parsed.get("product_name", "").strip()
        barcode = parsed.get("barcode", "").strip()

        if not product_name and not barcode:
            return _input_error("At least one of product_name or barcode is required.")

        allergen_raw = parsed.get("allergen_constraints", [])
        if isinstance(allergen_raw, str):
            allergen_constraints = [a.strip() for a in allergen_raw.split(",") if a.strip()]
        else:
            allergen_constraints = list(allergen_raw) if allergen_raw else []

        query_context = {
            "store_id": parsed.get("store_id", ""),
            "time_of_day": parsed.get("time_of_day", ""),
            "season": parsed.get("season", ""),
            "store_cluster": parsed.get("store_cluster", ""),
            "allergen_constraints": allergen_constraints,
        }

        emit_trace_event(
            "PreProcessNode_request_normalized",
            {
                "has_product_name": bool(product_name),
                "has_barcode": bool(barcode),
                "store_id": query_context["store_id"],
                "time_of_day": query_context["time_of_day"],
                "allergen_count": len(allergen_constraints),
            },
            state,
        )

        return {
            "validated_input": raw.strip(),
            "query_product_name": product_name,
            "query_barcode": barcode,
            "query_context": query_context,
            "status": AgentStatus.SUCCESS.value,
        }

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        """S-3: Verify no individual customer identifier leaked into output."""
        context = result.get("query_context", {})
        if isinstance(context, dict) and _CUSTOMER_ID_PATTERN.search(str(context)):
            raise SecurityViolationError("PreProcessNode: customer identifier detected in query_context output")
        return result


def _parse_request(raw: str) -> dict | None:
    """Parse JSON or colon-delimited key:value request. Returns None if unparseable."""
    raw = raw.strip()
    # Try JSON first
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    # Try key:value lines
    result: dict = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result if result else None
