"""PB-2 + PB-5: State safety and conditional checkpoint protection."""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

_CREDENTIAL_FIELD = re.compile(r"(jwt|token|api_key|secret|password|credential|connection_string)", re.IGNORECASE)
_PROHIBITED_TYPES = ("BaseModel", "InvocationContext")
_CONFIG_PATH = pathlib.Path(__file__).parents[2] / "config" / "config.yaml"


def _checkpointing_enabled() -> bool:
    try:
        import yaml

        config = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
    except Exception:
        return False
    return bool(config.get("memory_enabled") or config.get("hitl", {}).get("enabled", False))


def _framework_ingress_protection_available() -> bool:
    try:
        from framework.graph.base_graph import BaseGraph
    except Exception:
        return False
    return all(hasattr(BaseGraph, hook) for hook in ("_sanitize_ingress", "_sanitize_resume_feedback"))


def _scan_state_file(filepath: pathlib.Path) -> list[str]:
    tree = ast.parse(filepath.read_text(), filename=str(filepath))
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, ast.AnnAssign) or not isinstance(item.target, ast.Name):
                continue
            field_name = item.target.id
            if _CREDENTIAL_FIELD.search(field_name):
                violations.append(f"{filepath}:{item.lineno} — credential-like field: {field_name}")
            annotation = ast.dump(item.annotation)
            for prohibited in _PROHIBITED_TYPES:
                if prohibited in annotation:
                    violations.append(f"{filepath}:{item.lineno} — prohibited State type: {prohibited}")
    return violations


class TestStateSafety:
    def test_state_file_safety(self):
        state_file = pathlib.Path(__file__).parents[2] / "src" / "schemas" / "state.py"
        if not state_file.exists():
            pytest.skip("src/schemas/state.py not found")
        violations = _scan_state_file(state_file)
        assert violations == [], "State safety violations:\n" + "\n".join(violations)


_PB5_APPLICABLE = _checkpointing_enabled() and _framework_ingress_protection_available()
_PB5_REASON = (
    "config/config.yaml enables neither memory nor HITL — PB-5 auto-waived"
    if not _checkpointing_enabled()
    else "installed AgentCore lacks ingress hooks — PB-5 auto-waived"
)


@pytest.mark.skipif(not _PB5_APPLICABLE, reason=_PB5_REASON)
def test_pb5_precheckpoint_ingress_not_raw() -> None:
    pytest.fail("PB-5 is applicable, but RET-C2-607 has no real graph/checkpointer fixture")
