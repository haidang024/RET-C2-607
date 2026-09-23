"""RET-C2-607 Cat 2 outer AgentBaseGraph — CVS Personalized Product Recommendation Agent."""

from __future__ import annotations

from typing import Any, ClassVar, cast

from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.post_process_node import PostProcessNode
from src.nodes.pre_process_node import PreProcessNode
from src.schemas.state import State


# Customer-facing failure reasons (Harness H3).
#
# framework/nodes/base_node.py stores error_log entries as
# f"[{node_name}] {exc}\n{traceback.format_exc()}". Marketplace Chat renders
# `output` verbatim, so the raw entry would leak node class names, absolute file
# paths and line numbers to the end user.
_SAFE_REASONS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("not yet wired", "notimplementederror"), "RECOMMENDATION_SOURCE_UNAVAILABLE"),
    (("missingsecret", "required secret", "missing required config"), "CONFIGURATION_MISSING"),
    (("authentication", "unauthorized", "401"), "AUTHENTICATION_FAILED"),
    (("ratelimit", "rate limit", "too many requests", "429"), "RATE_LIMITED"),
    (("timeout", "timed out"), "LLM_TIMEOUT"),
    (("connecterror", "connection refused", "proxyerror"), "CONNECTION_FAILED"),
)

_SAFE_REASON_TEXT: dict[str, str] = {
    "RECOMMENDATION_SOURCE_UNAVAILABLE": (
        "The product-pairing knowledge base is not available in this environment, "
        "so no recommendations could be produced."
    ),
    "CONFIGURATION_MISSING": "A required credential is not configured for this agent in this environment.",
    "AUTHENTICATION_FAILED": "The configured language-model credential was rejected.",
    "RATE_LIMITED": "The recommendation service is rate limiting requests.",
    "LLM_TIMEOUT": "The recommendation service did not respond in time.",
    "CONNECTION_FAILED": "The recommendation service could not be reached.",
    "INTERNAL_PROCESSING_ERROR": "The recommendation could not be completed because of an internal error.",
}


def _safe_reason(error_log: object) -> str:
    """Map raw framework error_log entries to one customer-safe line.

    Never returns node names, file paths, line numbers or traceback text.
    """
    entries = [str(e) for e in error_log] if isinstance(error_log, (list, tuple)) else []
    haystack = " ".join(entries).lower()
    for needles, code in _SAFE_REASONS:
        if any(n in haystack for n in needles):
            return f"{_SAFE_REASON_TEXT[code]} (Reference: {code})"
    code = "INTERNAL_PROCESSING_ERROR"
    return f"{_SAFE_REASON_TEXT[code]} (Reference: {code})"


class RecommendationWorkflowGraphNode(GraphNode):
    """GraphNode wrapper for the inner RecommendationWorkflowGraph; assigned to `main` slot.

    Wraps the 5-node recommendation pipeline:
      ProductResolve → PairingKBRetrieve → StoreContext → AllergenCheck → RecommendRank
    """

    # "handle", not "propagate": a propagated SubgraphError ends the run with
    # status=error, and the Marketplace runner then drops `output` and shows the
    # caller a bare RuntimeError with no reason (Harness G2/G3).
    error_strategy: ClassVar[str] = "handle"
    propagate_hitl: ClassVar[bool] = False
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def __init__(self, config: dict | None = None, llm: object | None = None) -> None:
        self._config = config or {}
        self._llm = llm
        super().__init__()

    def get_subgraph(self) -> AgentBaseGraph:
        from src.graph.domain_workflow_graph import RecommendationWorkflowGraph

        return RecommendationWorkflowGraph(config=self._parent_config())

    def extract_input(self, state: AgentState) -> dict:
        return {
            "query_product_name": state.get("query_product_name", ""),
            "query_barcode": state.get("query_barcode", ""),
            "query_context": state.get("query_context", {}),
            "status": state.get("status", AgentStatus.SUCCESS.value),
            "error_log": state.get("error_log", []),
        }

    def on_subgraph_error(self, state: AgentState, error: Exception) -> dict[str, Any]:
        """Report an inner failure through the caller-visible guidance channel.

        Reported on a SUCCESS envelope because the Marketplace runner only
        forwards `output` when status == "success"; status=error would leave the
        caller with no reason at all (Harness G3/H6).
        """
        del state
        error_log = getattr(error, "error_log", None) or []
        return {
            "status": AgentStatus.SUCCESS.value,
            "input_error_message": _safe_reason(error_log),
        }

    def merge_output(self, state: AgentState, sub_result: dict) -> dict:
        """Map inner graph output → outer state. Returns only changed keys."""
        return {
            "ranked_recommendations": sub_result.get("ranked_recommendations", []),
            "status": sub_result.get("status"),
            "error_log": sub_result.get("error_log", state.get("error_log", [])),
        }

    def execute(self, state: AgentState) -> dict[str, Any]:
        if state.get("input_error_message"):
            return {"status": AgentStatus.SUCCESS.value}
        return cast(dict[str, Any], super().execute(state))

    def _parent_config(self) -> dict:
        """Pass runtime dependencies and service settings into the inner graph."""
        return {
            "llm": self._llm,
            "kb_path": self._config.get("kb_path", "./kb/"),
            "stg_mock_mode": bool(self._config.get("stg_mock_mode", False)),
        }


class Graph(AgentBaseGraph):
    """RET-C2-607 — Retail CVS Personalized Product Recommendation Agent.

    Cat 2: outer AgentBaseGraph backbone + GraphNode wrapping the inner
    5-node recommendation workflow.
    Backbone: initialize → pre_process → main → post_process → finalize (fixed).
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    # Harness J2: runner 1.0.1 calls agent_cls(); 1.0.3 calls agent_cls(config=...).
    # **kwargs absorbs arguments added by later runner versions.
    def __init__(self, config: dict | None = None, **kwargs: Any) -> None:
        super().__init__(config=config, **kwargs)

    @property
    def name(self) -> str:
        return "ret_c2_607_product_recommendation_agent"

    @property
    def state_schema(self) -> type:
        return State

    def register_nodes(self) -> None:
        super().register_nodes()  # injects: initialize, finalize
        self._nodes["pre_process"] = PreProcessNode()
        self._nodes["main"] = RecommendationWorkflowGraphNode(
            config=self.config,
            llm=self.config.get("llm"),
        )
        self._nodes["post_process"] = PostProcessNode(
            llm=self.config.get("llm"),
            config=self.config,
        )

    def get_output(self, state: AgentState) -> dict[str, Any]:
        output = {
            "output": (
                state.get("formatted_output")
                or state.get("output_response")
                or state.get("report_artefact")
                or state.get("result", "")
            ),
            "result": state.get("result", ""),
            "status": state.get("status", AgentStatus.ERROR.value),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
            "generation_mode": state.get("generation_mode"),
            "provider_error_message": state.get("provider_error_message"),
        }
        context = state.get("input_context")
        is_marketplace = isinstance(context, dict) and "conversation_history" in context
        if not is_marketplace:
            return output
        if _set_marketplace_guidance(output, state, "Product recommendation request"):
            return output
        payload = output.get("output", output.get("formatted_output"))
        if isinstance(payload, dict):
            output["output"] = self._render_marketplace_recommendations(payload)
        return output

    @staticmethod
    def _render_marketplace_recommendations(payload: dict[str, Any]) -> str:
        recommendations = payload.get("recommendations")
        lines = [
            "# Product Recommendations",
            "",
            f"**Matches found:** {payload.get('count', len(recommendations) if isinstance(recommendations, list) else 0)}",
        ]
        if isinstance(recommendations, list) and recommendations:
            lines.extend(["", "## Recommended products", ""])
            for index, item in enumerate(recommendations, start=1):
                if not isinstance(item, dict):
                    continue
                name = item.get("product_name", item.get("product_id", f"Product {index}"))
                category = item.get("category")
                product_id = item.get("product_id")
                details = [str(value) for value in (category, product_id) if value]
                suffix = f" — {'; '.join(details)}" if details else ""
                lines.append(f"{index}. **{name}**{suffix}")
        else:
            lines.extend(["", "No safe product recommendations were found."])

        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            lines.extend(["", "## Processing notes", ""])
            lines.extend(f"- {error}" for error in errors)
        return "\n".join(lines)


def _set_marketplace_guidance(output: dict[str, Any], state: AgentState, subject: str) -> bool:
    context = state.get("input_context")
    message = state.get("input_error_message")
    if not (isinstance(context, dict) and "conversation_history" in context and message):
        return False
    lines = [f"{subject} could not be processed.", "", f"Reason: {message}"]
    guidance = state.get("input_error_guidance")
    if isinstance(guidance, list) and guidance:
        lines.extend(["", "How to continue:"])
        lines.extend(f"- {item}" for item in guidance)
    output["output"] = "\n".join(lines)
    return True
