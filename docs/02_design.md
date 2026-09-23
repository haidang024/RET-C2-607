# Template Design Specification

## Position in AgentCore Architecture

- **Agent Class**: `Graph`
- **L1 Base**: **AgentBaseGraph**
- **Three-Layer Separation**:
  - State: flat TypedDict composition (no Pydantic — msgpack incompatible)
  - Node: L1 inheritance (Template Method: `execute(self, state: dict) -> dict` override only)
  - Graph: composition (`register_nodes()` for node substitution)

## Architecture Overview

### Node Configuration

**Outer backbone (AgentBaseGraph slots):**

| Node | Responsibility | Input State Keys | Output State Keys | Inherits/Overrides |
|------|---------------|-----------------|------------------|--------------------|
| initialize | Framework bootstrap | — | correlation_id, session_id, status | InitializeNode (default) |
| pre_process | Parse & validate request; S-2 APPI gate | user_input / input_context | validated_input, query_product_name, query_barcode, query_context | PreProcessNode (VERIFIED_EXTERNAL) |
| main | Run inner domain workflow via GraphNode | validated_input, query_* | ranked_recommendations, status, error_log | RecommendationWorkflowGraphNode |
| post_process | Format output; S-3 strip forbidden keys | ranked_recommendations | formatted_output | PostProcessNode (VERIFIED_EXTERNAL) |
| finalize | Framework teardown | — | — | FinalizeNode (default) |

**Inner domain workflow (BaseGraph via GraphNode):**

| Node | Responsibility | Input | Output | Trust Level |
|------|---------------|-------|--------|-------------|
| ProductResolveNode | Match name/barcode → product_id | query_product_name, query_barcode | resolved_product_id, resolve_status | ANONYMOUS |
| PairingKBRetrieveNode | Fetch aggregate pairing candidates; filter individual records | resolved_product_id | pairing_candidates | ANONYMOUS |
| StoreContextNode | Filter by time_of_day / season / store_cluster | pairing_candidates, query_context | filtered_candidates | ANONYMOUS |
| AllergenCheckNode | Japan 28-allergen gate; fail-safe for missing metadata | filtered_candidates, allergen_constraints | safe_candidates | ANONYMOUS |
| RecommendRankNode | Score = pairing_score + context boosts; top-5; strip forbidden keys | safe_candidates | ranked_recommendations | ANONYMOUS |

### Data Flow

```
START → initialize → pre_process → main (GraphNode) → post_process → finalize → END
                                         |
                         ┌───────────────▼──────────────────────────────────┐
                         │  RecommendationWorkflowGraph (BaseGraph, inner)  │
                         │                                                   │
                         │  ProductResolve → PairingKBRetrieve →            │
                         │  StoreContext → AllergenCheck → RecommendRank    │
                         └───────────────────────────────────────────────────┘
```

### State Definition

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| validated_input | str | Raw sanitised input from PreProcessNode | Yes |
| query_product_name | str | Product name extracted from request | Yes |
| query_barcode | str | Barcode extracted from request (empty if absent) | Yes |
| query_context | dict | Store context: store_id, time_of_day, season, store_cluster, allergen_constraints | Yes |
| resolved_product_id | str | Product ID resolved from name/barcode | After ProductResolve |
| resolved_product_name | str | Canonical product name | After ProductResolve |
| resolve_status | str | "found" / "not_found" / "ambiguous" | After ProductResolve |
| pairing_candidates | list[dict] | Aggregate pairing records from KB | After PairingKBRetrieve |
| filtered_candidates | list[dict] | Candidates after store-context filter | After StoreContext |
| safe_candidates | list[dict] | Candidates after allergen gate | After AllergenCheck |
| ranked_recommendations | list[dict] | Top-N display-safe recommendations | After RecommendRank |

**State Constraints (mandatory):**
- Flat TypedDict only (primitives + JSON-serializable types)
- No JWT, API keys, credentials in State (checkpoint DB leakage)
- InvocationContext is recovered by framework nodes through `InvocationContext.from_state(state)`; it is never stored as a State field
- No Pydantic models, dataclass, arbitrary Python objects (msgpack incompatible)

## Framework Utilization

### Shared Components Used
- [x] InvocationContext — constructed by the authenticated HTTP adapter and propagated by AgentCore
- [ ] ConnectionPolicy — not used (mock KB; production KB wiring TBD)
- [x] SecurityViolationError — raised by PreProcessNode S-2 gate on customer_id / oversized input
- [x] S-2: `_extra_security_gate_input()` — implemented in PreProcessNode: rejects individual-customer identifiers and enforces the 2048-character size limit
- [x] S-3: `_extra_security_gate_output()` — implemented in PreProcessNode, RecommendRankNode, PostProcessNode: strips `customer_id`, `transaction_id`, `purchase_history`, `member_id` from all output dicts
- [x] S-4: `emit_trace_event()` — implemented in every `execute()` across all 7 nodes

> **S-2/S-3 gate behaviour by node type (ADR-017):**
> - `FunctionNode` subclass → framework `@final` gate always runs automatically;
>   extend via `_extra_security_gate_input()` / `_extra_security_gate_output()` only
> - `GraphNode` / `RemoteAgentNode` → deliberate no-op (upstream or remote node's gate already applied)
> - Custom `BaseNode` subclass → must implement `_security_gate_input()` and
>   `_security_gate_output()` directly (`@abstractmethod` — omission raises `TypeError` at instantiation)

### Composition Pattern

- **Pattern**: GraphNode (subgraph) — `RecommendationWorkflowGraphNode` wraps `RecommendationWorkflowGraph` in the outer backbone's `main` slot
- **Composition target**: `RecommendationWorkflowGraph(BaseGraph)` — linear 5-node inner pipeline
- **Error propagation strategy**: Inner nodes set `status=error` + append to `error_log` on failure; outer `merge_output()` lifts `status` and `error_log` to the outer state

### Runtime Configuration and Optional LLM Injection

Static registry metadata lives at the root of `config/agent.yaml`; runtime service, memory, and HITL settings live in `config/config.yaml`. The standalone adapter remains credential-free at import time:

```python
self._nodes["main"] = RecommendationWorkflowGraphNode(
    config=self.config,
    llm=self.config.get("llm"),
)
```

`RecommendationWorkflowGraphNode` passes runtime settings into its subgraph. KB filtering, allergen enforcement, scoring, and ranking remain deterministic. Post-processing requests a non-sensitive Azure OpenAI quality advisory; provider failure is isolated without changing results.

### Trust Boundary

The manifest, outer graph, pre/post nodes, and `main` GraphNode require `VERIFIED_EXTERNAL`. The five inner nodes remain `ANONYMOUS` because they are reachable only through that verified outer boundary and operate on aggregate, prevalidated state. The standalone adapter maps only the ordinary invocation bearer to `VERIFIED_EXTERNAL`; it never promotes that credential to `INTERNAL`.

## EU AI Act Art.13 Design-Time Evidence

The proposal declares this aggregate retail product-recommendation use case outside Annex III, so high-risk-system Art.13 evidence is not applicable.

## HITL Design

`config/config.yaml` sets `hitl.enabled: false` and `memory_enabled: false`. No node calls LangGraph `interrupt()` and the workflow completes synchronously.

## Import Isolation Confirmation
- [x] Template does not import agenticstar-platform SDK (Level 0)
- [x] Import targets: `framework/` and `shared/` only (no `agents/base/` required)

## Design Decision Record

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| L1 base type | AgentBaseGraph | AutonomousBaseGraph | AgentBaseGraph | Deterministic pipeline; no autonomous loop needed |
| Inner workflow pattern | Flat FunctionNodes in outer backbone | GraphNode (BaseGraph subgraph) | GraphNode | 5-node domain pipeline benefits from BaseGraph routing + node_history isolation |
| KB compliance boundary | Filter at retrieval (node) | Filter at input gate (PreProcessNode) | Both | Defence-in-depth: `_is_aggregate_record` at retrieval + S-2 rejection at input |
| Allergen metadata missing | Fail-safe exclude | Pass-through | Fail-safe exclude | Safety-first: unknown allergen data must not reach customer |
| Trust level — inner nodes | ANONYMOUS | VERIFIED_EXTERNAL | ANONYMOUS | Trust verified once at outer boundary; inner nodes trust-trap anti-pattern applies |
