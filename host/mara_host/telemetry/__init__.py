# mara_host/telemetry/__init__.py
"""
Telemetry parsing and logging.

This is an INTERNAL module. Telemetry data is typically accessed via
Robot.telemetry or the TelemetryHostModule.

Internal API (for mara_host submodules):
    - TelemetryPacket: Parsed telemetry data container
    - TelemetryHostModule: Runtime module for telemetry events
    - TelemetryFileLogger: Log telemetry to JSONL files
    - parse_telemetry: Parse JSON telemetry messages
    - parse_telemetry_bin: Parse binary telemetry messages
    - Telemetry models: ImuTelemetry, EncoderTelemetry, etc.
"""

from .models import (
    TelemetryPacket,
    ImuTelemetry,
    UltrasonicTelemetry,
    LidarTelemetry,
    EncoderTelemetry,
    StepperTelemetry,
    DcMotorTelemetry,
    SignalTelemetry,
    ControlSignalsTelemetry,
    ObserverTelemetry,
    ControlObserversTelemetry,
    ControlSlotTelemetry,
    ControlSlotsTelemetry,
)
from .parser import parse_telemetry
from .binary_parser import parse_telemetry_bin
from .host_module import TelemetryHostModule
from .file_logger import TelemetryFileLogger

__all__ = [
    # Main types
    "TelemetryPacket",
    "TelemetryHostModule",
    "TelemetryFileLogger",
    # Parsers
    "parse_telemetry",
    "parse_telemetry_bin",
    # Telemetry models
    "ImuTelemetry",
    "UltrasonicTelemetry",
    "LidarTelemetry",
    "EncoderTelemetry",
    "StepperTelemetry",
    "DcMotorTelemetry",
    "SignalTelemetry",
    "ControlSignalsTelemetry",
    "ObserverTelemetry",
    "ControlObserversTelemetry",
    "ControlSlotTelemetry",
    "ControlSlotsTelemetry",
]
