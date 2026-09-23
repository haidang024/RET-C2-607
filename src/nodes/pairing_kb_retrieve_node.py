"""PairingKBRetrieveNode — retrieve aggregate product-pairing candidates from KB."""

from __future__ import annotations

from typing import ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

TOP_K = 20  # maximum aggregate pairing candidates to retrieve

# Individual-data field names that must not appear in aggregate KB records
_INDIVIDUAL_DATA_KEYS = frozenset(
    [
        "customer_id",
        "user_id",
        "member_id",
        "card_no",
        "purchase_datetime",
        "transaction_id",
        "receipt_id",
        "顧客ID",
        "会員番号",
        "取引ID",
    ]
)


class PairingKBRetrieveNode(FunctionNode):
    """Retrieve aggregate frequently-bought-together pairing candidates from the KB.

    Inner graph node — runs at ANONYMOUS.
    Retrieves ONLY approved aggregate data; records with individual-data fields
    are rejected and not propagated downstream.
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def __init__(self, config: dict | None = None) -> None:
        super().__init__()
        self._config = config or {}

    def execute(self, state: dict) -> dict:
        if state.get("status") == AgentStatus.ERROR.value:
            emit_trace_event(
                "PairingKBRetrieveNode_skipped_upstream_error",
                {"reason": "upstream error"},
                state,
            )
            return {}

        resolved_product_id = state.get("resolved_product_id", "")
        if not resolved_product_id:
            emit_trace_event(
                "PairingKBRetrieveNode_no_product_id",
                {"outcome": "error"},
                state,
            )
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": state.get("error_log", []) + ["PairingKBRetrieveNode: resolved_product_id is empty"],
            }

        from src.services.pairing_kb_service import PairingKbService

        service = PairingKbService(
            kb_path=str(self._config.get("kb_path", "./kb/")),
            stg_mock_mode=bool(
                state.get(
                    "stg_mock_mode",
                    self._config.get("stg_mock_mode", False),
                )
            ),
        )
        raw_candidates = service.retrieve_pairings(resolved_product_id, top_k=TOP_K)

        # Reject individual-data-shaped records (APPI aggregate-only boundary)
        safe_candidates = [c for c in raw_candidates if _is_aggregate_record(c)]
        rejected_count = len(raw_candidates) - len(safe_candidates)

        emit_trace_event(
            "PairingKBRetrieveNode_retrieved",
            {
                "product_id": resolved_product_id,
                "candidate_count": len(safe_candidates),
                "rejected_individual_data_count": rejected_count,
            },
            state,
        )

        if not safe_candidates:
            return {
                "pairing_candidates": [],
                "status": AgentStatus.ERROR.value,
                "error_log": state.get("error_log", [])
                + ["PairingKBRetrieveNode: no aggregate pairing candidates available"],
            }

        return {
            "pairing_candidates": safe_candidates,
            "status": AgentStatus.SUCCESS.value,
        }


def _is_aggregate_record(record: object) -> bool:
    """True if the record contains no individual-data fields."""
    if not isinstance(record, dict):
        return False
    return not any(key in record for key in _INDIVIDUAL_DATA_KEYS)
