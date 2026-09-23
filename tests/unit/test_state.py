"""TC-01: State contract — flat TypedDict, no Pydantic/dataclass, no credentials."""

from __future__ import annotations

import typing


class TestStateContract:
    """TC-01: State must be a flat TypedDict (msgpack-safe)."""

    def test_state_is_typeddict(self):
        from src.schemas.state import State

        assert issubclass(State, dict), "State must be a TypedDict subclass (dict subtype)"

    def test_state_has_required_fields(self):
        from src.schemas.state import State

        hints = typing.get_type_hints(State)
        required = [
            "validated_input",
            "query_product_name",
            "query_barcode",
            "query_context",
            "resolved_product_id",
            "resolved_product_name",
            "resolve_status",
            "pairing_candidates",
            "filtered_candidates",
            "safe_candidates",
            "ranked_recommendations",
        ]
        for field in required:
            assert field in hints, f"State missing required field: {field}"

    def test_state_no_credential_fields(self):
        from src.schemas.state import State
        import re

        hints = typing.get_type_hints(State)
        cred_pattern = re.compile(r"(jwt|token|api_key|secret|password|credential)", re.IGNORECASE)
        violations = [f for f in hints if cred_pattern.search(f)]
        assert not violations, f"Credential-like fields in State: {violations}"

    def test_state_no_pydantic_types(self):
        import os

        state_file = os.path.join(os.path.dirname(__file__), "..", "..", "src", "schemas", "state.py")
        with open(state_file) as f:
            source = f.read()
        assert "BaseModel" not in source, "State must not use Pydantic BaseModel"
        assert "InvocationContext" not in source, "InvocationContext must not be in State"
