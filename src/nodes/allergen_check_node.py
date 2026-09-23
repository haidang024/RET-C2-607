"""AllergenCheckNode — apply Japan food-label 28-allergen constraint gate."""

from __future__ import annotations

from typing import ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

# Japan 食品表示基準 28-allergen set (JAS / 消費者庁)
# 特定原材料 (8) — mandatory labeling under 食品表示基準 第3条
_SPECIFIED_MANDATORY_8: frozenset[str] = frozenset(
    [
        "えび",
        "かに",
        "小麦",
        "そば",
        "卵",
        "乳",
        "落花生",
        "ピーナッツ",
        "くるみ",
    ]
)
# 特定原材料に準ずるもの (20) — recommended labeling
_SPECIFIED_RECOMMENDED_20: frozenset[str] = frozenset(
    [
        "アーモンド",
        "あわび",
        "いか",
        "いくら",
        "オレンジ",
        "カシューナッツ",
        "キウイフルーツ",
        "牛肉",
        "ごま",
        "さけ",
        "さば",
        "大豆",
        "鶏肉",
        "バナナ",
        "豚肉",
        "まつたけ",
        "もも",
        "やまいも",
        "りんご",
        "ゼラチン",
    ]
)
SPECIFIED_ALLERGENS_28: frozenset[str] = _SPECIFIED_MANDATORY_8 | _SPECIFIED_RECOMMENDED_20

# Product categories that carry food allergen metadata
_FOOD_CATEGORIES = frozenset(["food", "dairy", "sweets", "bakery", "deli"])


class AllergenCheckNode(FunctionNode):
    """Apply Japan food-label 28-allergen gate to pairing candidates.

    Inner graph node — runs at ANONYMOUS.
    Food products conflicting with declared allergen constraints are excluded.
    Food products with MISSING allergen metadata are excluded (safe default).
    Non-food products (beverages, etc.) pass through unconditionally.
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict) -> dict:
        if state.get("status") == AgentStatus.ERROR.value:
            emit_trace_event(
                "AllergenCheckNode_skipped_upstream_error",
                {"reason": "upstream error"},
                state,
            )
            return {}

        candidates = state.get("filtered_candidates", [])
        query_context = state.get("query_context", {})
        declared: list[str] = query_context.get("allergen_constraints", [])
        declared_set = set(declared)

        safe_candidates, excluded_count = _apply_allergen_gate(candidates, declared_set)

        emit_trace_event(
            "AllergenCheckNode_gate_applied",
            {
                "input_count": len(candidates),
                "safe_count": len(safe_candidates),
                "excluded_count": excluded_count,
                "declared_allergen_count": len(declared),
            },
            state,
        )

        return {
            "safe_candidates": safe_candidates,
            "status": AgentStatus.SUCCESS.value,
        }


def _apply_allergen_gate(
    candidates: list[dict],
    declared_allergens: set[str],
) -> tuple[list[dict], int]:
    """Return (safe_candidates, excluded_count).

    Exclusion rules:
    - Food product with conflicting allergens → excluded.
    - Food product with None/missing allergen metadata → excluded (fail-safe).
    - Non-food product → always included.
    """
    safe: list[dict] = []
    excluded = 0
    for c in candidates:
        category = c.get("category", "")
        is_food = category in _FOOD_CATEGORIES

        if not is_food:
            safe.append(c)
            continue

        product_allergens = c.get("allergens")
        if product_allergens is None:
            # Missing metadata → exclude safely
            excluded += 1
            continue

        if declared_allergens & set(product_allergens):
            excluded += 1
        else:
            safe.append(c)

    return safe, excluded
