"""Regression coverage for readable Marketplace input guidance."""

from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel

from src.graph.graph import Graph


def test_invalid_marketplace_request_returns_readable_guidance() -> None:
    result = Graph().invoke(
        "Hello, hi",
        ctx=InvocationContext(caller_trust_level=TrustLevel.INTERNAL),
        input_context={"conversation_history": []},
    )

    assert result["status"] == "success"
    assert result["output"].startswith("Product recommendation request could not be processed.")
    assert "Reason:" in result["output"]
    assert "How to continue:" in result["output"]


def test_success_output_is_readable_only_for_marketplace() -> None:
    graph = Graph()
    canonical = {
        "recommendations": [{"product_id": "P003", "product_name": "Green Tea 500ml", "category": "beverage"}],
        "count": 1,
    }
    state = {"formatted_output": canonical, "status": "success"}

    assert graph.get_output(state)["output"] == canonical

    marketplace = graph.get_output({**state, "input_context": {"conversation_history": []}})
    assert marketplace["output"].startswith("# Product Recommendations")
    assert "Green Tea 500ml" in marketplace["output"]
    assert "P003" in marketplace["output"]
    assert isinstance(marketplace["output"], str)
