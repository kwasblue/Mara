# mara_host/motor/__init__.py
"""
Motor control modules.

This is an INTERNAL module. For public API, use:
    from mara_host import Servo, Stepper, DCMotor

Internal API (for mara_host submodules):
    - MotionHostModule: Differential drive motion module
    - PillCarousel, PillCarouselConfig: Pill dispenser application
"""

from .motion import MotionHostModule
from .pill_carousel import PillCarousel, PillCarouselConfig

__all__ = [
    "MotionHostModule",
    "PillCarousel",
    "PillCarouselConfig",
]
