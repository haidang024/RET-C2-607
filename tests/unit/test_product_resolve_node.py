"""Unit tests for ProductResolveNode (inner, ANONYMOUS)."""

from __future__ import annotations

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.product_resolve_node import ProductResolveNode, _resolve_product


class TestProductResolveNode:
    """BL/TC-11 — ProductResolveNode tests."""

    def setup_method(self):
        self.node = ProductResolveNode()

    def test_required_trust_level_is_anonymous(self):
        """Inner domain nodes must be ANONYMOUS (trust-trap anti-pattern check)."""
        assert ProductResolveNode.required_trust_level == TrustLevel.ANONYMOUS

    def test_resolves_by_exact_name(self, base_state):
        state = {**base_state, "query_product_name": "おにぎり 鮭", "query_barcode": ""}
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["resolved_product_id"] == "P001"
        assert result["resolve_status"] == "found"

    def test_resolves_by_barcode(self, base_state):
        state = {**base_state, "query_product_name": "", "query_barcode": "4901234567892"}
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["resolved_product_id"] == "P003"

    def test_fuzzy_match(self, base_state):
        state = {**base_state, "query_product_name": "緑茶", "query_barcode": ""}
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["resolved_product_id"] == "P003"

    def test_not_found_returns_error(self, base_state):
        state = {**base_state, "query_product_name": "存在しない商品XYZ", "query_barcode": ""}
        result = self.node(state)
        assert result["status"] == AgentStatus.ERROR.value
        assert result["resolved_product_id"] == ""
        assert result["resolve_status"] == "not_found"

    def test_no_input_returns_error(self, base_state):
        state = {**base_state, "query_product_name": "", "query_barcode": ""}
        result = self.node(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_skips_on_upstream_error(self, base_state):
        """Node must short-circuit and return {} when upstream set status=error."""
        state = {
            **base_state,
            "status": AgentStatus.ERROR.value,
            "query_product_name": "おにぎり 鮭",
            "query_barcode": "",
        }
        result = self.node(state)
        # __call__() adds node_history/execution_time to the {} returned by execute()
        assert result.get("resolved_product_id") is None
        assert result.get("resolve_status") is None

    def test_s4_emit_called(self, base_state, monkeypatch):
        """TC-11: emit_trace_event fires inside execute()."""
        import src.nodes.product_resolve_node as mod

        captured = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a: captured.append(a))
        state = {**base_state, "query_product_name": "おにぎり 鮭", "query_barcode": ""}
        self.node(state)
        assert captured


class TestResolveProduct:
    """Unit tests for the _resolve_product helper."""

    def test_exact_name(self):
        pid, name, status = _resolve_product("おにぎり 鮭", "")
        assert pid == "P001"
        assert status == "found"

    def test_barcode_priority(self):
        pid, name, status = _resolve_product("wrong name", "4901234567890")
        assert pid == "P001"
        assert status == "found"

    def test_unknown_product(self):
        pid, name, status = _resolve_product("XYZ不明商品", "0000000000000")
        assert pid == ""
        assert status == "not_found"
