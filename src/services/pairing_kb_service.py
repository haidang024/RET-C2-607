"""PairingKbService — aggregate product-pairing KB retrieval service.

Retrieves frequently-bought-together pairing signals from the approved
aggregate KB. Never accesses individual customer purchase records.
"""

from __future__ import annotations

import logging
from typing import Any

from src.services.mock_mode import mock_mode_enabled

logger = logging.getLogger(__name__)


class PairingKbService:
    """Aggregate product-pairing retrieval service.

    Retrieves pairing candidates from the aggregate KB for a given canonical
    product_id. All records must be aggregate — no individual customer data.

    Usage from a node::

        service = PairingKbService()
        candidates = service.retrieve_pairings(product_id, top_k=20)
    """

    def __init__(self, kb_path: str = "./kb/", stg_mock_mode: bool = False) -> None:
        self._kb_path = kb_path
        # Runtime config is passed by the graph; STG/CI may also opt in via env.
        self._mock_mode: bool = mock_mode_enabled(stg_mock_mode)

    def retrieve_pairings(
        self,
        product_id: str,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Retrieve aggregate pairing candidates for the given product_id.

        Args:
            product_id: Canonical product ID from the product catalog.
            top_k: Maximum number of aggregate pairing candidates to return.

        Returns:
            List of aggregate pairing dicts. Each record must have:
            {product_id, product_name, category, pairing_score, allergens,
             time_tags, season_tags, store_cluster_tags}
        """
        if not product_id:
            raise ValueError("PairingKbService.retrieve_pairings: product_id is empty")
        return self._call_kb(product_id, top_k)

    def _call_kb(self, product_id: str, top_k: int) -> list[dict[str, Any]]:
        if self._mock_mode:
            from src.services.mock_data import stub_retrieve_pairings

            return stub_retrieve_pairings(product_id, top_k)
        raise NotImplementedError(
            "PairingKbService._call_kb: production KB client not yet wired. "
            f"Wire shared/services/<vector_client> against kb_path={self._kb_path!r}."
        )
