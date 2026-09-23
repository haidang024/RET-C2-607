"""Unit tests for PreProcessNode (outer boundary, VERIFIED_EXTERNAL)."""

from __future__ import annotations

import pytest

from framework.errors import SecurityViolationError
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.pre_process_node import PreProcessNode, _parse_request


class TestPreProcessNode:
    """TC-03/TC-08/TC-09/TC-11 — PreProcessNode boundary tests."""

    def setup_method(self):
        self.node = PreProcessNode()

    # ── Trust level ──────────────────────────────────────────────────────────

    def test_required_trust_level_is_verified_external(self):
        """TC-08: PreProcessNode must be VERIFIED_EXTERNAL (outer boundary)."""
        assert PreProcessNode.required_trust_level == TrustLevel.VERIFIED_EXTERNAL

    # ── Happy path ───────────────────────────────────────────────────────────

    def test_json_input_parsed(self, base_state):
        """BL-01: JSON input is parsed into structured query context."""
        state = {
            **base_state,
            "user_input": '{"product_name": "おにぎり 鮭", "store_id": "S001", "time_of_day": "morning"}',
        }
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["query_product_name"] == "おにぎり 鮭"
        assert result["query_context"]["store_id"] == "S001"
        assert result["query_context"]["time_of_day"] == "morning"

    def test_key_value_input_parsed(self, base_state):
        """BL-02: Colon-delimited key:value input is parsed correctly."""
        state = {
            **base_state,
            "user_input": "product_name: 緑茶 500ml\nstore_id: S002\ntime_of_day: lunch",
        }
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["query_product_name"] == "緑茶 500ml"

    def test_allergen_constraints_parsed(self, base_state):
        """BL-03: allergen_constraints parsed from JSON list."""
        state = {
            **base_state,
            "user_input": '{"product_name": "おにぎり 鮭", "allergen_constraints": ["乳", "小麦"]}',
        }
        result = self.node(state)
        assert result["query_context"]["allergen_constraints"] == ["乳", "小麦"]

    def test_barcode_input(self, base_state):
        """BL-04: barcode-only request is accepted."""
        state = {
            **base_state,
            "user_input": '{"barcode": "4901234567890", "store_id": "S001"}',
        }
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["query_barcode"] == "4901234567890"

    def test_user_input_is_the_only_raw_request_surface(self, base_state):
        """Raw ingress is not duplicated into input_context/checkpoint metadata."""
        state = {
            **base_state,
            "user_input": '{"product_name": "サンドイッチ ハムチーズ"}',
        }
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["query_product_name"] == "サンドイッチ ハムチーズ"

    # ── Error paths ──────────────────────────────────────────────────────────

    def test_empty_input_returns_guidance(self, base_state):
        state = {**base_state, "user_input": ""}
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["input_error_message"]

    def test_missing_product_name_and_barcode_returns_guidance(self, base_state):
        state = {**base_state, "user_input": '{"store_id": "S001"}'}
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert "product_name" in result["input_error_message"]

    # ── Security gates ───────────────────────────────────────────────────────

    def test_s2_rejects_customer_id_field(self, base_state):
        """TC-09/S-2: individual customer_id in input raises SecurityViolationError."""
        state = {
            **base_state,
            "user_input": '{"product_name": "tea", "customer_id": "C123"}',
        }
        with pytest.raises(SecurityViolationError, match="customer identifier"):
            self.node._extra_security_gate_input(state)

    def test_s2_rejects_member_id(self, base_state):
        """TC-09/S-2: 会員番号 in input raises SecurityViolationError."""
        state = {**base_state, "user_input": "会員番号: M001\nproduct_name: tea"}
        with pytest.raises(SecurityViolationError):
            self.node._extra_security_gate_input(state)

    def test_s2_rejects_oversized_input(self, base_state):
        """TC-09/S-2: input exceeding MAX_INPUT_CHARS raises SecurityViolationError."""
        state = {**base_state, "user_input": "x" * 3000}
        with pytest.raises(SecurityViolationError, match="exceeds"):
            self.node._extra_security_gate_input(state)

    def test_s2_returns_state(self, base_state):
        """§9-ZB: _extra_security_gate_input must return state (not None)."""
        state = {**base_state, "user_input": '{"product_name": "tea"}'}
        result = self.node._extra_security_gate_input(state)
        assert result is state

    def test_s3_gate_returns_result(self, base_state):
        """§9-ZB: _extra_security_gate_output must return result dict."""
        result = {"query_context": {"store_id": "S001"}, "status": "success"}
        out = self.node._extra_security_gate_output(result)
        assert out is result

    # ── emit_trace_event ─────────────────────────────────────────────────────

    def test_s4_emit_called(self, base_state, monkeypatch):
        """TC-11/S-4: emit_trace_event fires at least once inside execute()."""
        import src.nodes.pre_process_node as mod

        captured = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a: captured.append(a))
        state = {
            **base_state,
            "user_input": '{"product_name": "おにぎり 鮭"}',
        }
        self.node(state)
        assert captured, "emit_trace_event must be called at least once"
        assert all(len(a) == 3 for a in captured), "emit_trace_event must receive 3 args"


class TestParseRequest:
    """Unit tests for the _parse_request helper."""

    def test_json_object(self):
        result = _parse_request('{"product_name": "tea"}')
        assert result == {"product_name": "tea"}

    def test_key_value(self):
        result = _parse_request("product_name: tea\nstore_id: S001")
        assert result["product_name"] == "tea"
        assert result["store_id"] == "S001"

    def test_unparseable_returns_none(self):
        result = _parse_request("no colon here, no json either")
        assert result is None

    def test_empty_returns_none(self):
        result = _parse_request("")
        assert result is None
