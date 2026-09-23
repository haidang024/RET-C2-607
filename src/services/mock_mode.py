"""mock_mode — single source of truth for mock-mode detection."""

from __future__ import annotations

import os


def mock_mode_enabled(stg_mock_mode: bool = False) -> bool:
    """Return True when running in STG/CI mock mode.

    Runtime config is authoritative for deployed agents. STG/CI can also opt in
    through its documented environment flags without placing deployment details
    in graph State.
    """
    env_value = os.environ.get("STG_MOCK_MODE", os.environ.get("USE_MOCK", ""))
    return stg_mock_mode or env_value.strip().lower() in {"1", "true", "yes", "on"}
