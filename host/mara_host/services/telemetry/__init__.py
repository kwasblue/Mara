# mara_host/services/telemetry/__init__.py
"""
Telemetry services for subscribing to and processing robot data.

Provides a high-level interface for telemetry streams.

Example:
    from mara_host.services.telemetry import TelemetryService

    telem = TelemetryService(client)
    telem.subscribe_imu(on_imu_callback)
    telem.subscribe_encoders(on_encoder_callback)

    # Get latest values
    imu_data = telem.get_latest_imu()
"""

from mara_host.services.telemetry.telemetry_service import (
    TelemetryService,
    TelemetrySnapshot,
    ImuData,
    EncoderData,
)

__all__ = [
    "TelemetryService",
    "TelemetrySnapshot",
    "ImuData",
    "EncoderData",
]
