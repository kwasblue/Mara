# mara_host/hw/__init__.py
"""
Hardware abstraction modules: GPIO, PWM.

This is an INTERNAL module. For public API, use:
    from mara_host import GPIO, PWM

Internal API (for mara_host submodules):
    - GpioModule: Low-level GPIO host module
    - PwmModule: Low-level PWM host module
"""

from .gpio import GpioHostModule
from .pwm import PwmHostModule

__all__ = [
    "GpioHostModule",
    "PwmHostModule",
]
