# mara_host/services/pins/__init__.py
"""
Pin management services.

This module provides the business logic layer for GPIO pin management.
Use PinService for validation, conflict detection, and recommendations.
"""

from .models import (
    PinConflict,
    PinRecommendation,
    GroupRecommendation,
)
from .groups import PIN_GROUPS
from .service import PinService

__all__ = [
    "PinService",
    "PinConflict",
    "PinRecommendation",
    "GroupRecommendation",
    "PIN_GROUPS",
]
