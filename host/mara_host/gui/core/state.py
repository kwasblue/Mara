# mara_host/gui/core/state.py
"""
Application state management for the GUI.

Provides dataclasses for tracking application state
and connection status.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

from mara_host.core._generated_config import DEFAULT_BAUD_RATE


class ConnectionState(str, Enum):
    """Connection state enum."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class DeviceCapabilities:
    """
    Device capabilities from firmware identity response.

    Used to dynamically show/hide GUI sections based on
    what features the connected device supports.
    """

    # Raw values from firmware
    features: List[str] = field(default_factory=list)
    capabilities_mask: int = 0

    # Convenience properties for feature checking
    @property
    def has_dc_motor(self) -> bool:
        return "dc_motor" in self.features

    @property
    def has_servo(self) -> bool:
        return "servo" in self.features

    @property
    def has_stepper(self) -> bool:
        return "stepper" in self.features

    @property
    def has_imu(self) -> bool:
        return "imu" in self.features

    @property
    def has_encoder(self) -> bool:
        return "encoder" in self.features

    @property
    def has_gpio(self) -> bool:
        return "gpio" in self.features

    @property
    def has_pwm(self) -> bool:
        return "pwm" in self.features

    @property
    def has_telemetry(self) -> bool:
        return "telemetry" in self.features

    @property
    def has_motion_ctrl(self) -> bool:
        return "motion_ctrl" in self.features

    @property
    def has_signal_bus(self) -> bool:
        return "signal_bus" in self.features

    @property
    def has_control_kernel(self) -> bool:
        return "control_kernel" in self.features

    @property
    def has_wifi(self) -> bool:
        return "wifi" in self.features

    @property
    def has_any_motor(self) -> bool:
        return self.has_dc_motor or self.has_servo or self.has_stepper

    @property
    def has_any_sensor(self) -> bool:
        return self.has_imu or self.has_encoder

    def has_feature(self, name: str) -> bool:
        """Check if a specific feature is available."""
        return name in self.features

    def summary(self) -> str:
        """Return a summary of available features."""
        if not self.features:
            return "No features reported"
        return ", ".join(self.features)


@dataclass
class TransportConfig:
    """Transport configuration."""

    transport_type: str = "serial"  # serial, tcp, can
    # Serial
    port: str = ""
    baudrate: int = DEFAULT_BAUD_RATE
    # TCP
    host: str = "192.168.4.1"
    tcp_port: int = 3333


@dataclass
class AppState:
    """
    Application state container.

    Tracks all GUI-relevant state in a single dataclass.
    """

    # Connection
    connection_state: ConnectionState = ConnectionState.DISCONNECTED
    transport_config: TransportConfig = field(default_factory=TransportConfig)

    # Robot state
    robot_state: str = "UNKNOWN"
    firmware_version: str = ""
    protocol_version: int = 0

    # Device capabilities (from firmware identity)
    capabilities: DeviceCapabilities = field(default_factory=DeviceCapabilities)

    # Telemetry
    telemetry_enabled: bool = False
    telemetry_interval_ms: int = 50

    # Camera
    camera_streaming: bool = False
    camera_url: str = ""
    camera_fps: float = 0.0

    # Session
    recording_active: bool = False
    session_name: str = ""

    # UI state
    current_panel: str = "dashboard"
    estop_active: bool = False

    # Last error
    last_error: Optional[str] = None

    def copy(self) -> "AppState":
        """Create a copy of this state."""
        return AppState(
            connection_state=self.connection_state,
            transport_config=TransportConfig(
                transport_type=self.transport_config.transport_type,
                port=self.transport_config.port,
                baudrate=self.transport_config.baudrate,
                host=self.transport_config.host,
                tcp_port=self.transport_config.tcp_port,
            ),
            robot_state=self.robot_state,
            firmware_version=self.firmware_version,
            protocol_version=self.protocol_version,
            capabilities=DeviceCapabilities(
                features=list(self.capabilities.features),
                capabilities_mask=self.capabilities.capabilities_mask,
            ),
            telemetry_enabled=self.telemetry_enabled,
            telemetry_interval_ms=self.telemetry_interval_ms,
            camera_streaming=self.camera_streaming,
            camera_url=self.camera_url,
            camera_fps=self.camera_fps,
            recording_active=self.recording_active,
            session_name=self.session_name,
            current_panel=self.current_panel,
            estop_active=self.estop_active,
            last_error=self.last_error,
        )

    @property
    def is_connected(self) -> bool:
        """Check if connected to robot."""
        return self.connection_state == ConnectionState.CONNECTED

    @property
    def is_armed(self) -> bool:
        """Check if robot is armed."""
        return self.robot_state in ("ARMED", "ACTIVE")

    @property
    def is_active(self) -> bool:
        """Check if robot is in active mode."""
        return self.robot_state == "ACTIVE"
