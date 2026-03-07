# mara_host/sensor/__init__.py
"""
Sensor modules: encoder, IMU, ultrasonic.

This is an INTERNAL module. For public API, use:
    from mara_host import Encoder, IMU, Ultrasonic

Internal API (for mara_host submodules):
    - EncoderModule: Low-level encoder host module
    - ImuModule: Low-level IMU host module
    - UltrasonicModule: Low-level ultrasonic host module
"""

from .encoder import EncoderHostModule
from .imu import ImuHostModule
from .ultrasonic import UltrasonicHostModule

__all__ = [
    "EncoderHostModule",
    "ImuHostModule",
    "UltrasonicHostModule",
]
