"""Compiled outer-graph integration coverage for RET-C2-607."""

import json

from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel

from src.graph.graph import Graph


def test_compiled_graph_returns_safe_recommendations() -> None:
    graph = Graph(config={"kb_path": "./kb/", "stg_mock_mode": True, "llm": None})
    graph.compile()

    result = graph.invoke(
        json.dumps(
            {
                "product_name": "おにぎり 鮭",
                "store_id": "S01",
                "time_of_day": "morning",
                "season": "all",
            },
            ensure_ascii=False,
        ),
        ctx=InvocationContext(
            session_id="integration-test",
            caller_trust_level=TrustLevel.VERIFIED_EXTERNAL,
            caller_id="integration-test",
        ),
    )

    assert result["status"] == "success"
    assert result["output"]["count"] > 0
    assert all(
        set(recommendation) <= {"product_id", "product_name", "category"}
        for recommendation in result["output"]["recommendations"]
    )
