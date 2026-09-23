"""State — RET-C2-607 Retail CVS Personalized Product Recommendation Agent."""

# ADR-005: State must be a flat TypedDict. LangGraph checkpoints use msgpack
# serialization — only plain serializable fields are allowed.
# APPI boundary: never store individual customer identifiers or raw purchase
# records. query_context.allergen_constraints is request-time staff/kiosk
# input only and contains no persistent customer profile data.

from __future__ import annotations

from framework.schemas.agent_state import AgentState


class State(AgentState):
    """Agent state for the CVS product recommendation workflow.

    All shared fields (user_input, status, session_id, node_history,
    error_log, hitl_*, etc.) are inherited from AgentState.

    Business boundary: aggregate-only product-pairing KB.
    Never store individual customer identifiers or raw purchase records.
    """

    # Input — set by PreProcessNode
    validated_input: str
    query_product_name: str  # product name extracted from staff/kiosk request
    query_barcode: str  # optional product barcode; "" if absent
    query_context: dict  # {store_id, time_of_day, season, store_cluster,
    #                            allergen_constraints: list[str]}
    #                          allergen_constraints = request-time declaration;
    #                          not a stored customer profile.

    # ProductResolve step
    resolved_product_id: str  # canonical product ID from catalog; "" if not found
    resolved_product_name: str  # canonical product name; "" if not found
    resolve_status: str  # "found" | "not_found" | "ambiguous"

    # PairingKBRetrieve step
    pairing_candidates: list[dict]  # aggregate KB pairing results (no individual data)

    # StoreContext step
    filtered_candidates: list[dict]  # candidates after store/season/time-of-day filter

    # AllergenCheck step
    safe_candidates: list[dict]  # candidates after 28-allergen gate

    # RecommendRank step
    ranked_recommendations: list[dict]  # final ranked top-N recommendations (safe fields only)

    # User-correctable input guidance
    input_error_message: str | None
    input_error_guidance: list[str]

    # Invocation-scoped provider observability (never contains secret details)
    generation_mode: str | None
    provider_error_message: str | None
