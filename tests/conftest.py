"""conftest.py — test fixtures for RET-C2-607."""

from __future__ import annotations

import pytest


@pytest.fixture
def base_state() -> dict:
    """Minimal state dict providing the fields InvocationContext.from_state() requires."""
    return {
        "correlation_id": "test-correlation-id",
        "session_id": "test-session-id",
        "thread_id": "test-thread-id",
        "trace_id": "test-trace-id",
        "caller_trust_level": "VERIFIED_EXTERNAL",
        "node_history": [],
        "error_log": [],
    }


@pytest.fixture
def recommendation_state(base_state) -> dict:
    """State with a resolved product + populated pairing candidates."""
    return {
        **base_state,
        "validated_input": '{"product_name": "おにぎり 鮭", "store_id": "S001"}',
        "query_product_name": "おにぎり 鮭",
        "query_barcode": "",
        "query_context": {
            "store_id": "S001",
            "time_of_day": "morning",
            "season": "winter",
            "store_cluster": "urban",
            "allergen_constraints": [],
        },
        "resolved_product_id": "P001",
        "resolved_product_name": "おにぎり 鮭",
        "resolve_status": "found",
        "stg_mock_mode": True,
    }
