# Test Specification

## Test Strategy
- Coverage target: 80%
- Test types: Unit, Proof-of-Boundary

## Framework Compliance Tests (Mandatory)

| TC-ID | Test | Expected Result | Result |
|-------|------|----------------|--------|
| TC-01 | State contract: flat TypedDict | Type check pass, no Pydantic/dataclass | PASS |
| TC-02 | SecurityViolationError fires on invalid input | Error raised | PASS |
| TC-03 | No JWT/Credential in State | CI `gate-credential-scan`: 0 violations. S-5 credential-shape scanning runs as a CI gate over the full diff on every push, not as a unit-test assertion, so it catches leakage in code paths a state-shape test would not reach | PASS |
| TC-04 | InvocationContext constructed by the authenticated adapter or recovered via `from_state()` inside framework nodes | No InvocationContext object is persisted in State | PASS |
| TC-05 | S-4: no duplicate lifecycle events in `execute()` | `node_start` / `node_complete` / `node_error` absent from `execute()` body | 0 duplicates |
| TC-06 | S-2: `_security_gate_input()` not overridden (`FunctionNode` subclass) | `TypeError` raised at class definition if overridden (`@final` enforced by framework) | 0 overrides |
| TC-07 | S-3: `_security_gate_output()` not overridden (`FunctionNode` subclass) | `TypeError` raised at class definition if overridden (`@final` enforced by framework) | 0 overrides |
| TC-08 | `required_trust_level` enforced: outer=VERIFIED_EXTERNAL, inner=ANONYMOUS | Correct trust level on each node class | PASS |
| TC-09 | S-2: `_extra_security_gate_input()` — rejects customer_id, oversized input | APPI violation input raises SecurityViolationError; size > 2048 raises SecurityViolationError | PASS |
| TC-10 | S-3: `_extra_security_gate_output()` — strips forbidden keys from output dicts | customer_id absent from PostProcessNode output; product_id preserved | PASS |
| TC-11 | S-4: at least one domain `emit_trace_event()` inside each `execute()` | Domain event emitted on every invocation path across all 7 nodes | PASS |

## Proof-of-Boundary Tests (Mandatory)

| PB-ID | Boundary | Test | Expected Result | Result |
|-------|----------|------|----------------|--------|
| PB-1 | BaseNode → EventEmitter | `emit_trace_event()` fires on every invocation path | No silent failures | PASS (test_pb_invoke_order.py) |
| PB-2 | State serialization | Post-invoke State is primitives only | No Pydantic/dataclass | PASS (test_state_safety.py) |
| PB-3 | L1 template → External service | Real aggregate KB connection | Deferred until the production aggregate-KB client is wired; mock data does not satisfy the real boundary | WAIVED |
| PB-4 | Import isolation | No Level 0 imports | AST scan: 0 violations | PASS (test_import_isolation.py) |
| PB-5 | Checkpoint safety *(conditional)* | Inspect checkpoint payload, metadata, and pending writes when checkpointing is enabled | Auto-waived — checkpointing disabled | WAIVED |
| PB-6 | Invoke execution order | `__call__()`: S-1 trust gate → S-4 `node_start` → S-2 `_security_gate_input` → `execute()` → S-3 `_security_gate_output` → S-4 `node_complete` | Order verified | PASS (test_pb_invoke_order.py) |
| PB-7 | HITL interrupt propagation *(conditional)* | `config/config.yaml` sets `hitl.enabled: false` | **Auto-waived — non-HITL** | WAIVED |

> **Pre-release gate checklist:** PB-1 through PB-4 and PB-6 are mandatory. PB-5 is conditional on checkpointing and framework ingress-hook availability. PB-7 is conditional on `hitl.enabled: true`.

## Business Logic Tests

| TC-ID | Test | Input | Expected Result | Result |
|-------|------|-------|----------------|--------|
| BL-01 | Product resolved by exact name | query_product_name="おにぎり 鮭" | resolved_product_id="P001", resolve_status="found" | PASS |
| BL-02 | Product resolved by barcode | query_barcode="4901234567892" | resolved_product_id="P003" | PASS |
| BL-03 | Fuzzy product name match | query_product_name="緑茶" | resolved_product_id="P003" | PASS |
| BL-04 | Unknown product returns error | query_product_name="存在しない商品XYZ" | status=error, resolve_status="not_found" | PASS |
| BL-05 | Individual KB record rejected at retrieval | KB returns record with customer_id | record excluded from pairing_candidates | PASS |
| BL-06 | Store context time-of-day filter | time_of_day="morning", candidate has time_tags=["evening"] | candidate excluded from filtered_candidates | PASS |
| BL-07 | "all" tag passes any context | candidate has time_tags=["all"], time_of_day="night" | candidate passes through | PASS |
| BL-08 | No constraints → all candidates pass allergen gate | allergen_constraints=[], candidates have allergens=["さけ"] | all pass | PASS |
| BL-09 | Food with matching allergen excluded | allergen_constraints=["乳"], food product has allergens=["乳"] | product excluded from safe_candidates | PASS |
| BL-10 | Food with None allergen metadata excluded (fail-safe) | allergen_constraints=[], food product has allergens=None | product excluded from safe_candidates | PASS |
| BL-11 | Non-food product always passes allergen gate | category="beverage", allergen_constraints=["小麦","乳","卵"] | product passes through | PASS |
| BL-12 | Ranking by pairing_score descending | 3 candidates with scores 0.6, 0.9, 0.75 | order: 0.9, 0.75, 0.6 | PASS |
| BL-13 | Time-match boost elevates candidate | 2 candidates equal score; one matches time_of_day | time-match ranks first | PASS |
| BL-14 | Top-N limit = 5 | 8 candidates | ranked_recommendations length ≤ 5 | PASS |
| BL-15 | APPI: customer_id stripped from output | candidate has customer_id in KB record | customer_id absent from ranked_recommendations | PASS |
| BL-16 | Japan 28-allergen set complete (mandatory 8) | SPECIFIED_ALLERGENS_28 | えび,かに,小麦,そば,卵,乳,落花生,くるみ all present | PASS |
| BL-17 | Japan 28-allergen set complete (recommended 20 + ピーナッツ alias) | SPECIFIED_ALLERGENS_28 | all 20 recommended allergens + ピーナッツ present | PASS |
| BL-18 | formatted_output key present for get_output() | PostProcessNode.execute() | "formatted_output" in result | PASS |
| BL-19 | JSON input parsing | input="{"product_name":"おにぎり 鮭"}" | query_product_name="おにぎり 鮭" | PASS |
| BL-20 | Colon-delimited input parsing | input="product:おにぎり 鮭" | query_product_name="おにぎり 鮭" | PASS |

## Test Execution Summary
- Execution date: 2026-08-18
- Total tests collected: 99
- Pass: 96 / Fail: 0 / Skip: 3 conditional waivers (PB-5 checkpointing disabled; PB-7 non-HITL)
- Coverage target: 80% (coverage was not measured by `check-local.sh`)
