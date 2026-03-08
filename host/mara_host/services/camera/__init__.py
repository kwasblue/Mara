# mara_host/services/camera/__init__.py
"""
Camera services for streaming and control.

Provides high-level interfaces for camera operations.

Example:
    from mara_host.services.camera import StreamService, CameraControlService

    stream = StreamService("http://10.0.0.60")
    stream.start()
    frame = stream.get_frame()

    control = CameraControlService(client)
    await control.set_resolution(8)  # VGA
"""

from mara_host.services.camera.stream_service import (
    StreamService,
    CameraFrame,
)
from mara_host.services.camera.camera_control_service import (
    CameraControlService,
    CameraConfig,
    Resolution,
)

__all__ = [
    "StreamService",
    "CameraFrame",
    "CameraControlService",
    "CameraConfig",
    "Resolution",
]
