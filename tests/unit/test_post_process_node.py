"""Unit tests for PostProcessNode (outer boundary, VERIFIED_EXTERNAL)."""

from __future__ import annotations

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.post_process_node import PostProcessNode


class TestPostProcessNode:
    """TC-08/TC-10/TC-11 — PostProcessNode tests."""

    def setup_method(self):
        self.node = PostProcessNode()

    def test_required_trust_level_is_verified_external(self):
        assert PostProcessNode.required_trust_level == TrustLevel.VERIFIED_EXTERNAL

    def test_formats_recommendations(self, base_state):
        """BL: ranked_recommendations appear in formatted_output."""
        recs = [{"product_id": "P003", "product_name": "緑茶 500ml", "category": "beverage"}]
        state = {
            **base_state,
            "ranked_recommendations": recs,
            "status": AgentStatus.SUCCESS.value,
        }
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["formatted_output"]["count"] == 1
        assert result["formatted_output"]["recommendations"] == recs

    def test_empty_recommendations(self, base_state):
        """BL: empty recommendations still produce a valid output."""
        state = {
            **base_state,
            "ranked_recommendations": [],
            "status": AgentStatus.SUCCESS.value,
        }
        result = self.node(state)
        assert result["formatted_output"]["count"] == 0

    def test_error_log_included(self, base_state):
        """BL: error_log entries from upstream appear in formatted_output["errors"]."""
        state = {
            **base_state,
            "ranked_recommendations": [],
            "error_log": ["some error"],
        }
        result = self.node(state)
        assert "errors" in result["formatted_output"]

    def test_s3_strips_forbidden_keys(self, base_state):
        """TC-10/S-3: customer_id stripped from output by _extra_security_gate_output."""
        result = {
            "formatted_output": {
                "recommendations": [{"product_id": "P001", "customer_id": "C999"}],
                "count": 1,
            },
            "status": "success",
        }
        out = self.node._extra_security_gate_output(result)
        rec = out["formatted_output"]["recommendations"][0]
        assert "customer_id" not in rec
        assert "product_id" in rec

    def test_s4_emit_called(self, base_state, monkeypatch):
        """TC-11/S-4: emit_trace_event fires inside execute()."""
        import src.nodes.post_process_node as mod

        captured = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a: captured.append(a))
        state = {**base_state, "ranked_recommendations": [], "status": "success"}
        self.node(state)
        assert captured

    def test_formatted_output_key_present(self, base_state):
        """§9-ZE: formatted_output key must be present for AgentBaseGraph.get_output()."""
        state = {**base_state, "ranked_recommendations": [], "status": "success"}
        result = self.node(state)
        assert "formatted_output" in result
