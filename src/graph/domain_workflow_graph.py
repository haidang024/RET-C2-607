"""RecommendationWorkflowGraph — inner 5-node CVS product recommendation pipeline."""

from __future__ import annotations

from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_status import AgentStatus
from framework.schemas.invocation_context import InvocationContext
from src.nodes.allergen_check_node import AllergenCheckNode
from src.nodes.pairing_kb_retrieve_node import PairingKBRetrieveNode
from src.nodes.product_resolve_node import ProductResolveNode
from src.nodes.recommend_rank_node import RecommendRankNode
from src.nodes.store_context_node import StoreContextNode
from src.schemas.state import State


class RecommendationWorkflowGraph(BaseGraph):
    """Inner domain graph for the CVS product recommendation workflow.

    Linear pipeline:
        START → product_resolve → pairing_kb_retrieve → store_context
              → allergen_check → recommend_rank → END

    Called by RecommendationWorkflowGraphNode.get_subgraph() in graph.py.
    """

    def __init__(self, config: dict | None = None) -> None:
        self._domain_input: dict = {}
        super().__init__(config)

    def invoke(
        self,
        user_input: str | dict,
        session_id: str = "",
        ctx: InvocationContext | None = None,
        input_context: dict | None = None,
    ) -> dict:
        """Adapt the GraphNode's structured input to BaseGraph's string API."""
        self._domain_input = dict(user_input) if isinstance(user_input, dict) else {}
        raw_input = "ret-c2-607-domain-request" if isinstance(user_input, dict) else user_input
        return super().invoke(
            raw_input,
            session_id=session_id,
            ctx=ctx,
            input_context=input_context,
        )

    @property
    def name(self) -> str:
        return "ret_c2_607_recommendation_workflow"

    @property
    def state_schema(self) -> type:
        return State

    def _validate_config(self) -> None:
        """No mandatory config keys for this inner graph."""

    def _extra_initial_state(self) -> dict:
        """Promote the GraphNode's structured delta into initial state."""
        return dict(self._domain_input)

    def register_nodes(self) -> None:
        # No super() call — BaseGraph.register_nodes() is abstract.
        # initialize/finalize are outer-graph concerns.
        self._nodes["product_resolve"] = ProductResolveNode()
        self._nodes["pairing_kb_retrieve"] = PairingKBRetrieveNode(config=self.config)
        self._nodes["store_context"] = StoreContextNode()
        self._nodes["allergen_check"] = AllergenCheckNode()
        self._nodes["recommend_rank"] = RecommendRankNode()

    def add_edges(self) -> None:
        self._sg.add_edge(START, "product_resolve")
        self._sg.add_edge("product_resolve", "pairing_kb_retrieve")
        self._sg.add_edge("pairing_kb_retrieve", "store_context")
        self._sg.add_edge("store_context", "allergen_check")
        self._sg.add_edge("allergen_check", "recommend_rank")
        self._sg.add_edge("recommend_rank", END)

    def route(self, state: State) -> str:
        """Required by BaseGraph ABC; linear topology — no conditional edges used."""
        return str(END) if state.get("status") == AgentStatus.ERROR.value else "recommend_rank"

    def get_output(self, state: State) -> dict:
        """Shape the sub_result dict consumed by merge_output() in graph.py."""
        return {
            "ranked_recommendations": state.get("ranked_recommendations", []),
            "status": state.get("status"),
            "error_log": state.get("error_log", []),
            "node_history": state.get("node_history", []),
        }
