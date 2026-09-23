"""PB-7: HITL interrupt propagation (conditional for non-HITL agents)."""

from __future__ import annotations

import pathlib

import pytest
import yaml

_CONFIG_PATH = pathlib.Path(__file__).parents[2] / "config" / "config.yaml"


def _hitl_enabled() -> bool:
    config = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
    hitl = config.get("hitl", {})
    return isinstance(hitl, dict) and bool(hitl.get("enabled", False))


pytestmark = pytest.mark.skipif(
    not _hitl_enabled(),
    reason="config/config.yaml sets hitl.enabled: false — PB-7 is not applicable",
)


def test_pb7_hitl_interrupt_propagates() -> None:
    pytest.fail("HITL is enabled, but RET-C2-607 has no interrupting node fixture")


def test_pb7_hitl_allowed_false_skips_interrupt() -> None:
    pytest.fail("HITL is enabled, but RET-C2-607 has no hitl_allowed guard fixture")
