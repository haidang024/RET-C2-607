"""Unit tests for StoreContextNode (inner, ANONYMOUS)."""

from __future__ import annotations

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.store_context_node import StoreContextNode


class TestStoreContextNode:
    """BL/TC-11 — StoreContextNode tests."""

    def setup_method(self):
        self.node = StoreContextNode()

    def test_required_trust_level_is_anonymous(self):
        assert StoreContextNode.required_trust_level == TrustLevel.ANONYMOUS

    def test_filters_by_time_of_day(self, base_state):
        state = {
            **base_state,
            "pairing_candidates": [
                {"product_id": "A", "time_tags": ["morning"], "season_tags": [], "store_cluster_tags": []},
                {"product_id": "B", "time_tags": ["evening"], "season_tags": [], "store_cluster_tags": []},
            ],
            "query_context": {"time_of_day": "morning", "season": "", "store_cluster": ""},
        }
        result = self.node(state)
        ids = [c["product_id"] for c in result["filtered_candidates"]]
        assert "A" in ids
        assert "B" not in ids

    def test_all_tag_matches_any_time(self, base_state):
        state = {
            **base_state,
            "pairing_candidates": [
                {"product_id": "A", "time_tags": ["all"], "season_tags": [], "store_cluster_tags": []},
            ],
            "query_context": {"time_of_day": "night", "season": "", "store_cluster": ""},
        }
        result = self.node(state)
        assert result["filtered_candidates"][0]["product_id"] == "A"

    def test_no_context_permissive(self, base_state):
        """When no context provided, all candidates pass through."""
        candidates = [
            {"product_id": "A", "time_tags": ["morning"], "season_tags": ["winter"], "store_cluster_tags": []},
            {"product_id": "B", "time_tags": [], "season_tags": [], "store_cluster_tags": []},
        ]
        state = {
            **base_state,
            "pairing_candidates": candidates,
            "query_context": {"time_of_day": "", "season": "", "store_cluster": ""},
        }
        result = self.node(state)
        assert len(result["filtered_candidates"]) == 2

    def test_filters_by_store_cluster(self, base_state):
        state = {
            **base_state,
            "pairing_candidates": [
                {"product_id": "A", "time_tags": [], "season_tags": [], "store_cluster_tags": ["urban"]},
                {"product_id": "B", "time_tags": [], "season_tags": [], "store_cluster_tags": ["rural"]},
            ],
            "query_context": {"time_of_day": "", "season": "", "store_cluster": "urban"},
        }
        result = self.node(state)
        ids = [c["product_id"] for c in result["filtered_candidates"]]
        assert "A" in ids
        assert "B" not in ids

    def test_skips_on_upstream_error(self, base_state):
        state = {**base_state, "status": AgentStatus.ERROR.value, "pairing_candidates": []}
        result = self.node(state)
        # __call__() adds node_history/execution_time to the {} returned by execute()
        assert result.get("filtered_candidates") is None

    def test_s4_emit_called(self, base_state, monkeypatch):
        import src.nodes.store_context_node as mod

        captured = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a: captured.append(a))
        state = {
            **base_state,
            "pairing_candidates": [],
            "query_context": {"time_of_day": "", "season": "", "store_cluster": ""},
        }
        self.node(state)
        assert captured
