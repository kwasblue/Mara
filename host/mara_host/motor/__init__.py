# mara_host/motor/__init__.py
"""
Motor control modules: servo, stepper, motion controller.

This is an INTERNAL module. For public API, use:
    from mara_host import Servo, Stepper, DCMotor

Internal API (for mara_host submodules):
    - ServoModule: Low-level servo host module
    - StepperModule: Low-level stepper host module
    - MotionModule: Differential drive motion module
    - PillCarousel, PillCarouselConfig: Pill dispenser application
"""

from .servo import ServoHostModule
from .stepper import StepperHostModule
from .motion import MotionHostModule
from .pill_carousel import PillCarousel, PillCarouselConfig

__all__ = [
    "ServoHostModule",
    "StepperHostModule",
    "MotionHostModule",
    "PillCarousel",
    "PillCarouselConfig",
]
