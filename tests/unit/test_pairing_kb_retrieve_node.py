"""Unit tests for PairingKBRetrieveNode (inner, ANONYMOUS)."""

from __future__ import annotations


from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.pairing_kb_retrieve_node import PairingKBRetrieveNode, _is_aggregate_record


class TestPairingKBRetrieveNode:
    """BL/TC-11 — PairingKBRetrieveNode tests."""

    def setup_method(self):
        self.node = PairingKBRetrieveNode()

    def test_required_trust_level_is_anonymous(self):
        assert PairingKBRetrieveNode.required_trust_level == TrustLevel.ANONYMOUS

    def test_retrieves_candidates_for_known_product(self, recommendation_state):
        """BL: aggregate pairing candidates returned for resolved product."""
        result = self.node(recommendation_state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert isinstance(result["pairing_candidates"], list)
        assert len(result["pairing_candidates"]) > 0

    def test_no_product_id_returns_error(self, base_state):
        state = {**base_state, "resolved_product_id": ""}
        result = self.node(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_skips_on_upstream_error(self, base_state):
        state = {**base_state, "status": AgentStatus.ERROR.value, "resolved_product_id": "P001"}
        result = self.node(state)
        # __call__() adds node_history/execution_time to the {} returned by execute()
        assert result.get("pairing_candidates") is None

    def test_individual_data_records_rejected(self, recommendation_state, monkeypatch):
        """APPI: records with customer_id/transaction_id are rejected."""

        individual_record = {
            "product_id": "P003",
            "product_name": "緑茶",
            "category": "beverage",
            "pairing_score": 0.9,
            "customer_id": "C001",  # individual data — must be rejected
            "transaction_id": "T999",
        }
        aggregate_record = {
            "product_id": "P006",
            "product_name": "コーヒー缶",
            "category": "beverage",
            "pairing_score": 0.7,
            "allergens": [],
            "time_tags": ["all"],
            "season_tags": ["all"],
            "store_cluster_tags": ["all"],
        }

        class MockService:
            def __init__(self, **kwargs):
                pass

            def retrieve_pairings(self, product_id, top_k=20):
                return [individual_record, aggregate_record]

        import src.services.pairing_kb_service as svc_module

        monkeypatch.setattr(svc_module, "PairingKbService", MockService)

        result = self.node(recommendation_state)
        # individual_record must be filtered out
        ids = [c["product_id"] for c in result.get("pairing_candidates", [])]
        assert "P003" not in ids, "Individual-data-shaped record must not propagate"
        assert "P006" in ids

    def test_s4_emit_called(self, recommendation_state, monkeypatch):
        import src.nodes.pairing_kb_retrieve_node as mod

        captured = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a: captured.append(a))
        self.node(recommendation_state)
        assert captured


class TestIsAggregateRecord:
    """Unit tests for the _is_aggregate_record guard."""

    def test_clean_aggregate_record(self):
        assert _is_aggregate_record({"product_id": "P001", "pairing_score": 0.8}) is True

    def test_record_with_customer_id(self):
        assert _is_aggregate_record({"product_id": "P001", "customer_id": "C001"}) is False

    def test_record_with_transaction_id(self):
        assert _is_aggregate_record({"product_id": "P001", "transaction_id": "T999"}) is False

    def test_non_dict_returns_false(self):
        assert _is_aggregate_record("not a dict") is False
