"""ProductResolveNode — resolve product name/barcode to canonical catalog product ID."""

from __future__ import annotations

from typing import ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event


class ProductResolveNode(FunctionNode):
    """Resolve product name or barcode to a canonical aggregate-KB product identifier.

    Inner graph node — runs at ANONYMOUS (trust verified at outer PreProcessNode).
    Resolves only against approved product catalog metadata.
    Ambiguous/unknown products produce a safe actionable error without data leakage.
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict) -> dict:
        if state.get("status") == AgentStatus.ERROR.value:
            emit_trace_event(
                "ProductResolveNode_skipped_upstream_error",
                {"reason": "upstream error"},
                state,
            )
            return {}

        product_name = state.get("query_product_name", "")
        barcode = state.get("query_barcode", "")

        if not product_name and not barcode:
            emit_trace_event(
                "ProductResolveNode_no_input",
                {"outcome": "error"},
                state,
            )
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": state.get("error_log", [])
                + ["ProductResolveNode: neither product_name nor barcode provided"],
            }

        resolved_id, resolved_name, resolve_status = _resolve_product(product_name, barcode)

        emit_trace_event(
            "ProductResolveNode_resolved",
            {
                "resolve_status": resolve_status,
                "resolved_product_id": resolved_id,
            },
            state,
        )

        if resolve_status == "not_found":
            return {
                "resolved_product_id": "",
                "resolved_product_name": "",
                "resolve_status": "not_found",
                "status": AgentStatus.ERROR.value,
                "error_log": state.get("error_log", []) + ["ProductResolveNode: product not found in catalog"],
            }

        return {
            "resolved_product_id": resolved_id,
            "resolved_product_name": resolved_name,
            "resolve_status": resolve_status,
            "status": AgentStatus.SUCCESS.value,
        }


# ---------------------------------------------------------------------------
# Aggregate catalog fixture (no individual customer data)
# ---------------------------------------------------------------------------

_PRODUCT_CATALOG: dict[str, dict] = {
    "P001": {"name": "おにぎり 鮭", "barcodes": ["4901234567890"], "category": "food"},
    "P002": {"name": "サンドイッチ ハムチーズ", "barcodes": ["4901234567891"], "category": "food"},
    "P003": {"name": "緑茶 500ml", "barcodes": ["4901234567892"], "category": "beverage"},
    "P004": {"name": "カップ麺 しょうゆ", "barcodes": ["4901234567893"], "category": "food"},
    "P005": {"name": "ヨーグルト プレーン", "barcodes": ["4901234567894"], "category": "dairy"},
    "P006": {"name": "コーヒー缶 ブラック", "barcodes": ["4901234567895"], "category": "beverage"},
    "P007": {"name": "チョコレートバー", "barcodes": ["4901234567896"], "category": "sweets"},
    "P008": {"name": "ミネラルウォーター 2L", "barcodes": ["4901234567897"], "category": "beverage"},
    "P009": {"name": "唐揚げ弁当", "barcodes": ["4901234567898"], "category": "food"},
    "P010": {"name": "アイスクリーム バニラ", "barcodes": ["4901234567899"], "category": "dairy"},
}

_NAME_INDEX: dict[str, str] = {info["name"]: pid for pid, info in _PRODUCT_CATALOG.items()}
_BARCODE_INDEX: dict[str, str] = {bc: pid for pid, info in _PRODUCT_CATALOG.items() for bc in info["barcodes"]}


def _resolve_product(product_name: str, barcode: str) -> tuple[str, str, str]:
    """Return (product_id, canonical_name, status). status: 'found'|'not_found'|'ambiguous'."""
    # Barcode exact match takes priority
    if barcode and barcode in _BARCODE_INDEX:
        pid = _BARCODE_INDEX[barcode]
        return pid, _PRODUCT_CATALOG[pid]["name"], "found"

    # Exact name match
    if product_name and product_name in _NAME_INDEX:
        pid = _NAME_INDEX[product_name]
        return pid, _PRODUCT_CATALOG[pid]["name"], "found"

    # Substring fuzzy match
    if product_name:
        matches = [
            (pid, info["name"])
            for pid, info in _PRODUCT_CATALOG.items()
            if product_name.lower() in info["name"].lower() or info["name"].lower() in product_name.lower()
        ]
        if len(matches) == 1:
            pid, name = matches[0]
            return pid, name, "found"
        if len(matches) > 1:
            pid, name = matches[0]
            return pid, name, "ambiguous"

    return "", "", "not_found"
