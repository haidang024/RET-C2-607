"""PostProcessNode — format ranked recommendations into safe API output."""

from __future__ import annotations

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.services.llm_runtime import provider_metadata, request_advisory

# Fields that must never appear in the final output (APPI boundary)
_FORBIDDEN_OUTPUT_KEYS = frozenset(
    [
        "customer_id",
        "user_id",
        "member_id",
        "card_no",
        "transaction_id",
        "purchase_datetime",
        "receipt_id",
        "顧客ID",
        "会員番号",
    ]
)


class PostProcessNode(FunctionNode):
    """Format ranked recommendations into the final safe response payload.

    Outer graph boundary node. Runs at VERIFIED_EXTERNAL.
    Defense-in-depth S-3 gate ensures no personal data escapes in the output.
    Sets formatted_output so AgentBaseGraph.get_output() populates the API response.
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def __init__(self, llm: object | None = None, config: dict | None = None) -> None:
        super().__init__()
        self._llm = llm
        self._config = config or {}

    def execute(self, state: dict) -> dict:
        if state.get("input_error_message"):
            message = str(state["input_error_message"])
            return {
                "formatted_output": message,
                "status": AgentStatus.SUCCESS.value,
                "input_error_message": message,
            }
        ranked_recommendations = state.get("ranked_recommendations", [])
        error_log = state.get("error_log", [])
        status = state.get("status", AgentStatus.SUCCESS.value)

        formatted_output = {
            "recommendations": ranked_recommendations,
            "count": len(ranked_recommendations),
        }
        if error_log:
            formatted_output["errors"] = error_log

        request_advisory(
            state,
            "Review the safety and clarity of a deterministic retail product recommendation response.",
            self._llm,
            timeout_s=float(self._config.get("timeout_s", 30)),
            max_retry=int(self._config.get("max_retry", 3)),
        )

        emit_trace_event(
            "PostProcessNode_output_formatted",
            {
                "recommendation_count": len(ranked_recommendations),
                "has_errors": bool(error_log),
                "status": status,
            },
            state,
        )

        return {
            "formatted_output": formatted_output,
            "status": status,
            **provider_metadata(state),
        }

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        """S-3: Strip any individual customer data from the formatted output."""
        formatted = result.get("formatted_output", {})
        if isinstance(formatted, dict):
            for rec in formatted.get("recommendations", []):
                if isinstance(rec, dict):
                    for key in list(rec.keys()):
                        if key in _FORBIDDEN_OUTPUT_KEYS:
                            rec.pop(key, None)
        return result
