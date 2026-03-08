# mara_host/sensor/__init__.py
"""
Sensor modules.

This is an INTERNAL module. For public API, use:
    from mara_host import Encoder

Internal API (for mara_host submodules):
    - EncoderHostModule: Low-level encoder host module
"""

from .encoder import EncoderHostModule

__all__ = [
    "EncoderHostModule",
]
