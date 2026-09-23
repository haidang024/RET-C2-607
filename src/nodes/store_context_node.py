"""StoreContextNode — apply time-of-day, seasonality, and store-cluster filtering."""

from __future__ import annotations

from typing import ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event


class StoreContextNode(FunctionNode):
    """Filter pairing candidates by time-of-day, season, and store-cluster context.

    Inner graph node — runs at ANONYMOUS.
    Uses only store/season/time context from the request; no customer profile inference.
    Candidates with no context tags are included (permissive default).
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict) -> dict:
        if state.get("status") == AgentStatus.ERROR.value:
            emit_trace_event(
                "StoreContextNode_skipped_upstream_error",
                {"reason": "upstream error"},
                state,
            )
            return {}

        candidates = state.get("pairing_candidates", [])
        query_context = state.get("query_context", {})

        time_of_day = query_context.get("time_of_day", "")
        season = query_context.get("season", "")
        store_cluster = query_context.get("store_cluster", "")

        filtered = _apply_context_filter(candidates, time_of_day, season, store_cluster)

        emit_trace_event(
            "StoreContextNode_filtered",
            {
                "input_count": len(candidates),
                "output_count": len(filtered),
                "time_of_day": time_of_day,
                "season": season,
                "store_cluster": store_cluster,
            },
            state,
        )

        return {
            "filtered_candidates": filtered,
            "status": AgentStatus.SUCCESS.value,
        }


def _apply_context_filter(
    candidates: list[dict],
    time_of_day: str,
    season: str,
    store_cluster: str,
) -> list[dict]:
    """Keep candidates whose tags match the provided context.

    A candidate with no tags for a given dimension is included (permissive default).
    A tag value of "all" always matches any context value.
    """
    result = []
    for c in candidates:
        time_tags: list[str] = c.get("time_tags", [])
        season_tags: list[str] = c.get("season_tags", [])
        cluster_tags: list[str] = c.get("store_cluster_tags", [])

        time_ok = not time_tags or not time_of_day or "all" in time_tags or time_of_day in time_tags
        season_ok = not season_tags or not season or "all" in season_tags or season in season_tags
        cluster_ok = not cluster_tags or not store_cluster or "all" in cluster_tags or store_cluster in cluster_tags

        if time_ok and season_ok and cluster_ok:
            result.append(c)
    return result
