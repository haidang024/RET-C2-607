"""Unit tests for PairingKbService (mock mode)."""

from __future__ import annotations

import pytest

from src.services.pairing_kb_service import PairingKbService


class TestPairingKbServiceMockMode:
    """BL/TC-11 — PairingKbService tests (USE_MOCK=true set in conftest)."""

    def setup_method(self):
        self.service = PairingKbService(stg_mock_mode=True)

    def test_returns_list_for_known_product(self):
        results = self.service.retrieve_pairings("P001", top_k=20)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_returns_empty_for_unknown_product(self):
        results = self.service.retrieve_pairings("P999", top_k=20)
        assert results == []

    def test_top_k_limits_results(self):
        results = self.service.retrieve_pairings("P001", top_k=1)
        assert len(results) <= 1

    def test_records_are_aggregate_only(self):
        """APPI: stub data must not contain individual customer fields."""
        results = self.service.retrieve_pairings("P001", top_k=20)
        for record in results:
            assert "customer_id" not in record, f"Individual data leaked: {record}"
            assert "transaction_id" not in record, f"Individual data leaked: {record}"

    def test_records_have_required_fields(self):
        results = self.service.retrieve_pairings("P001", top_k=20)
        for record in results:
            assert "product_id" in record
            assert "product_name" in record
            assert "category" in record
            assert "pairing_score" in record

    def test_production_mode_raises(self):
        """Outside mock mode, retrieve_pairings raises NotImplementedError."""
        svc = PairingKbService(stg_mock_mode=False)
        with pytest.raises(NotImplementedError):
            svc.retrieve_pairings("P001")
