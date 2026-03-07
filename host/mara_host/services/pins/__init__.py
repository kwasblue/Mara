# mara_host/services/pins/__init__.py
"""
Pin management services.

This module provides the business logic layer for GPIO pin management.
Use PinService for validation, conflict detection, and recommendations.
"""

from mara_host.services.pins.pin_service import (
    PinService,
    PinConflict,
    PinRecommendation,
    GroupRecommendation,
    PIN_GROUPS,
)

__all__ = [
    "PinService",
    "PinConflict",
    "PinRecommendation",
    "GroupRecommendation",
    "PIN_GROUPS",
]
