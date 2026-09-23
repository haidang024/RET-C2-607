"""Unit tests for RecommendRankNode (inner, ANONYMOUS)."""

from __future__ import annotations

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.recommend_rank_node import RecommendRankNode, _to_safe_output


class TestRecommendRankNode:
    """BL/TC-11 — RecommendRankNode tests."""

    def setup_method(self):
        self.node = RecommendRankNode()

    def test_required_trust_level_is_anonymous(self):
        assert RecommendRankNode.required_trust_level == TrustLevel.ANONYMOUS

    def test_ranks_by_pairing_score(self, base_state):
        """BL: candidates ranked descending by pairing_score."""
        candidates = [
            {
                "product_id": "P003",
                "product_name": "緑茶",
                "category": "beverage",
                "pairing_score": 0.6,
                "time_tags": [],
                "season_tags": [],
            },
            {
                "product_id": "P006",
                "product_name": "コーヒー缶",
                "category": "beverage",
                "pairing_score": 0.9,
                "time_tags": [],
                "season_tags": [],
            },
            {
                "product_id": "P002",
                "product_name": "お茶",
                "category": "beverage",
                "pairing_score": 0.75,
                "time_tags": [],
                "season_tags": [],
            },
        ]
        state = {
            **base_state,
            "safe_candidates": candidates,
            "query_context": {"time_of_day": "", "season": ""},
        }
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        ranked = result["ranked_recommendations"]
        # Check order
        assert ranked[0]["product_id"] == "P006"
        assert ranked[1]["product_id"] == "P002"
        assert ranked[2]["product_id"] == "P003"

    def test_top_n_limit(self, base_state):
        """BL: at most TOP_N (5) results returned."""
        candidates = [
            {
                "product_id": f"P{i:03d}",
                "product_name": f"商品{i}",
                "category": "beverage",
                "pairing_score": float(i) / 10,
                "time_tags": [],
                "season_tags": [],
            }
            for i in range(1, 9)
        ]
        state = {
            **base_state,
            "safe_candidates": candidates,
            "query_context": {"time_of_day": "", "season": ""},
        }
        result = self.node(state)
        assert len(result["ranked_recommendations"]) <= 5

    def test_context_boost_time_match(self, base_state):
        """BL: time-matching candidate scores higher than non-matching."""
        candidates = [
            {
                "product_id": "P003",
                "product_name": "緑茶",
                "category": "beverage",
                "pairing_score": 0.5,
                "time_tags": ["morning"],
                "season_tags": [],
            },
            {
                "product_id": "P006",
                "product_name": "コーヒー缶",
                "category": "beverage",
                "pairing_score": 0.5,
                "time_tags": ["evening"],
                "season_tags": [],
            },
        ]
        state = {
            **base_state,
            "safe_candidates": candidates,
            "query_context": {"time_of_day": "morning", "season": ""},
        }
        result = self.node(state)
        ranked_ids = [r["product_id"] for r in result["ranked_recommendations"]]
        assert ranked_ids[0] == "P003", "Time-matching candidate must rank first"

    def test_context_boost_season_match(self, base_state):
        """BL: season-matching candidate scores higher than non-matching."""
        candidates = [
            {
                "product_id": "P003",
                "product_name": "緑茶",
                "category": "beverage",
                "pairing_score": 0.5,
                "time_tags": [],
                "season_tags": ["summer"],
            },
            {
                "product_id": "P006",
                "product_name": "コーヒー缶",
                "category": "beverage",
                "pairing_score": 0.5,
                "time_tags": [],
                "season_tags": ["winter"],
            },
        ]
        state = {
            **base_state,
            "safe_candidates": candidates,
            "query_context": {"time_of_day": "", "season": "summer"},
        }
        result = self.node(state)
        ranked_ids = [r["product_id"] for r in result["ranked_recommendations"]]
        assert ranked_ids[0] == "P003", "Season-matching candidate must rank first"

    def test_empty_candidates(self, base_state):
        """BL: empty safe_candidates produces empty ranked_recommendations."""
        state = {
            **base_state,
            "safe_candidates": [],
            "query_context": {"time_of_day": "", "season": ""},
        }
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["ranked_recommendations"] == []

    def test_s3_output_strips_forbidden_keys(self, base_state):
        """S-3: customer_id / transaction_id must not appear in output."""
        candidates = [
            {
                "product_id": "P003",
                "product_name": "緑茶",
                "category": "beverage",
                "pairing_score": 0.9,
                "customer_id": "C001",
                "time_tags": [],
                "season_tags": [],
            },
        ]
        state = {
            **base_state,
            "safe_candidates": candidates,
            "query_context": {"time_of_day": "", "season": ""},
        }
        result = self.node(state)
        for rec in result["ranked_recommendations"]:
            assert "customer_id" not in rec
            assert "transaction_id" not in rec

    def test_skips_on_upstream_error(self, base_state):
        state = {**base_state, "status": AgentStatus.ERROR.value, "safe_candidates": []}
        result = self.node(state)
        # __call__() adds node_history/execution_time to the {} returned by execute()
        assert result.get("ranked_recommendations") is None

    def test_s4_emit_called(self, base_state, monkeypatch):
        import src.nodes.recommend_rank_node as mod

        captured = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a: captured.append(a))
        state = {**base_state, "safe_candidates": [], "query_context": {"time_of_day": "", "season": ""}}
        self.node(state)
        assert captured


class TestToSafeOutput:
    """Unit tests for _to_safe_output helper."""

    def test_keeps_display_fields(self):
        record = {
            "product_id": "P001",
            "product_name": "おにぎり 鮭",
            "category": "food",
            "pairing_score": 0.9,
            "customer_id": "C001",
            "transaction_id": "T999",
        }
        safe = _to_safe_output(record)
        assert safe["product_id"] == "P001"
        assert safe["product_name"] == "おにぎり 鮭"
        assert safe["category"] == "food"

    def test_strips_individual_data_fields(self):
        record = {"product_id": "P001", "customer_id": "C001", "transaction_id": "T999"}
        safe = _to_safe_output(record)
        assert "customer_id" not in safe
        assert "transaction_id" not in safe
