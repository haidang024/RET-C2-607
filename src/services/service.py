"""Service — re-export facade for PairingKbService.

Use PairingKbService directly for new code. This module exists for
scaffold-integrity compliance (src/services/ must have a non-stub module).
"""

from src.services.pairing_kb_service import PairingKbService as Service

__all__ = ["Service"]
