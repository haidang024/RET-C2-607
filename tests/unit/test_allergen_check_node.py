"""Unit tests for AllergenCheckNode (inner, ANONYMOUS) — Japan 28-allergen gate."""

from __future__ import annotations

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.allergen_check_node import (
    AllergenCheckNode,
    SPECIFIED_ALLERGENS_28,
)


class TestAllergenCheckNode:
    """BL/TC-11 — AllergenCheckNode tests."""

    def setup_method(self):
        self.node = AllergenCheckNode()

    def test_required_trust_level_is_anonymous(self):
        assert AllergenCheckNode.required_trust_level == TrustLevel.ANONYMOUS

    def test_no_constraints_all_pass(self, base_state):
        """No allergen constraints → all candidates pass through."""
        candidates = [
            {"product_id": "P003", "category": "beverage", "allergens": []},
            {"product_id": "P001", "category": "food", "allergens": ["さけ"]},
        ]
        state = {
            **base_state,
            "filtered_candidates": candidates,
            "query_context": {"allergen_constraints": []},
        }
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert len(result["safe_candidates"]) == 2

    def test_food_with_conflicting_allergen_excluded(self, base_state):
        """Food product containing a declared allergen is excluded."""
        candidates = [
            {"product_id": "P005", "category": "dairy", "allergens": ["乳"]},
            {"product_id": "P003", "category": "beverage", "allergens": []},
        ]
        state = {
            **base_state,
            "filtered_candidates": candidates,
            "query_context": {"allergen_constraints": ["乳"]},
        }
        result = self.node(state)
        safe_ids = [c["product_id"] for c in result["safe_candidates"]]
        assert "P005" not in safe_ids, "Dairy product with 乳 must be excluded"
        assert "P003" in safe_ids, "Beverage (non-food) must pass through"

    def test_food_missing_allergen_metadata_excluded(self, base_state):
        """Food product with None allergen metadata is excluded (fail-safe)."""
        candidates = [
            {"product_id": "P001", "category": "food", "allergens": None},
        ]
        state = {
            **base_state,
            "filtered_candidates": candidates,
            "query_context": {"allergen_constraints": []},
        }
        result = self.node(state)
        assert len(result["safe_candidates"]) == 0

    def test_non_food_always_passes(self, base_state):
        """Beverage products pass regardless of allergen constraints."""
        candidates = [
            {"product_id": "P003", "category": "beverage", "allergens": None},
            {"product_id": "P006", "category": "beverage", "allergens": []},
        ]
        state = {
            **base_state,
            "filtered_candidates": candidates,
            "query_context": {"allergen_constraints": ["小麦", "乳", "卵"]},
        }
        result = self.node(state)
        assert len(result["safe_candidates"]) == 2

    def test_skips_on_upstream_error(self, base_state):
        state = {**base_state, "status": AgentStatus.ERROR.value, "filtered_candidates": []}
        result = self.node(state)
        # __call__() adds node_history/execution_time to the {} returned by execute()
        assert result.get("safe_candidates") is None

    def test_s4_emit_called(self, base_state, monkeypatch):
        import src.nodes.allergen_check_node as mod

        captured = []
        monkeypatch.setattr(mod, "emit_trace_event", lambda *a: captured.append(a))
        state = {**base_state, "filtered_candidates": [], "query_context": {"allergen_constraints": []}}
        self.node(state)
        assert captured


class TestSpecifiedAllergens28:
    """Verify the 28-allergen constant coverage."""

    def test_mandatory_8_present(self):
        mandatory = ["えび", "かに", "小麦", "そば", "卵", "乳", "落花生", "くるみ"]
        for allergen in mandatory:
            assert allergen in SPECIFIED_ALLERGENS_28, f"Missing mandatory allergen: {allergen}"

    def test_recommended_20_present(self):
        recommended = [
            "アーモンド",
            "あわび",
            "いか",
            "いくら",
            "オレンジ",
            "カシューナッツ",
            "キウイフルーツ",
            "牛肉",
            "ごま",
            "さけ",
            "さば",
            "大豆",
            "鶏肉",
            "バナナ",
            "豚肉",
            "まつたけ",
            "もも",
            "やまいも",
            "りんご",
            "ゼラチン",
        ]
        for allergen in recommended:
            assert allergen in SPECIFIED_ALLERGENS_28, f"Missing recommended allergen: {allergen}"

    def test_peanut_aliases_present(self):
        assert "落花生" in SPECIFIED_ALLERGENS_28
        assert "ピーナッツ" in SPECIFIED_ALLERGENS_28
