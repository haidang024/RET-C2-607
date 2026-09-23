"""RecommendRankNode — rank eligible candidates and produce safe top-N output."""

from __future__ import annotations

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

TOP_N = 5  # default top-N recommendations returned

# Fields exposed in recommendation output (aggregate-safe display fields only)
_SAFE_OUTPUT_FIELDS = ("product_id", "product_name", "category")

# Fields that must never appear in output (APPI boundary)
_FORBIDDEN_OUTPUT_KEYS = frozenset(
    [
        "customer_id",
        "user_id",
        "transaction_id",
        "purchase_datetime",
        "顧客ID",
        "会員番号",
    ]
)


class RecommendRankNode(FunctionNode):
    """Rank eligible aggregate pairing candidates and produce top-N recommendations.

    Inner graph node — runs at ANONYMOUS.
    Score inputs: aggregate pairing_score + time-of-day/season context boost (±0.05 each).
    Output contains only display-safe aggregate fields; no raw KB records exposed.
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict) -> dict:
        if state.get("status") == AgentStatus.ERROR.value:
            emit_trace_event(
                "RecommendRankNode_skipped_upstream_error",
                {"reason": "upstream error"},
                state,
            )
            return {}

        candidates = state.get("safe_candidates", [])
        query_context = state.get("query_context", {})

        ranked = _rank_candidates(candidates, query_context)
        top_n = ranked[:TOP_N]
        recommendations = [_to_safe_output(c) for c in top_n]

        emit_trace_event(
            "RecommendRankNode_ranked",
            {
                "candidate_count": len(candidates),
                "top_n": len(recommendations),
            },
            state,
        )

        return {
            "ranked_recommendations": recommendations,
            "status": AgentStatus.SUCCESS.value,
        }

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        """S-3: Strip any individual-data fields that should not appear in output."""
        for rec in result.get("ranked_recommendations", []):
            if isinstance(rec, dict):
                for key in list(rec.keys()):
                    if key in _FORBIDDEN_OUTPUT_KEYS:
                        rec.pop(key, None)
        return result


def _rank_candidates(candidates: list[dict], query_context: dict) -> list[dict]:
    """Rank by aggregate pairing_score + context boost.

    Score inputs:
    - base: pairing_score (aggregate KB signal, 0.0–1.0)
    - +0.05 if candidate time_tags match time_of_day
    - +0.05 if candidate season_tags match season
    """
    time_of_day = query_context.get("time_of_day", "")
    season = query_context.get("season", "")

    scored: list[tuple[float, dict]] = []
    for c in candidates:
        score = float(c.get("pairing_score", 0.0))
        if time_of_day and time_of_day in c.get("time_tags", []):
            score += 0.05
        if season and season in c.get("season_tags", []):
            score += 0.05
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


def _to_safe_output(candidate: dict) -> dict:
    """Return display-safe aggregate recommendation record."""
    return {field: candidate.get(field, "") for field in _SAFE_OUTPUT_FIELDS}
