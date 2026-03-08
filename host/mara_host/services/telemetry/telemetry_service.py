# mara_host/services/telemetry/telemetry_service.py
"""
Telemetry service for subscribing to and processing robot data.

Provides a unified interface for telemetry streams from the robot.
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Any, TYPE_CHECKING
from collections import deque
import time

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class ImuData:
    """IMU sensor data."""

    ax: float = 0.0  # Acceleration X (m/s^2)
    ay: float = 0.0  # Acceleration Y (m/s^2)
    az: float = 0.0  # Acceleration Z (m/s^2)
    gx: float = 0.0  # Gyro X (rad/s)
    gy: float = 0.0  # Gyro Y (rad/s)
    gz: float = 0.0  # Gyro Z (rad/s)
    timestamp: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> "ImuData":
        """Create from telemetry dict."""
        return cls(
            ax=data.get("ax", 0.0),
            ay=data.get("ay", 0.0),
            az=data.get("az", 0.0),
            gx=data.get("gx", 0.0),
            gy=data.get("gy", 0.0),
            gz=data.get("gz", 0.0),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class EncoderData:
    """Encoder data for a single motor."""

    encoder_id: int
    ticks: int = 0
    velocity: float = 0.0  # rad/s or ticks/s depending on config
    timestamp: float = 0.0

    @classmethod
    def from_dict(cls, encoder_id: int, data: dict) -> "EncoderData":
        """Create from telemetry dict."""
        return cls(
            encoder_id=encoder_id,
            ticks=data.get("ticks", 0),
            velocity=data.get("velocity", 0.0),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class MotorData:
    """Motor state data."""

    motor_id: int
    speed: float = 0.0  # -1.0 to 1.0
    current: float = 0.0  # Amps (if available)
    timestamp: float = 0.0


@dataclass
class TelemetrySnapshot:
    """Complete telemetry snapshot at a point in time."""

    timestamp: float = 0.0
    state: str = "UNKNOWN"
    imu: Optional[ImuData] = None
    encoders: list[EncoderData] = field(default_factory=list)
    motors: list[MotorData] = field(default_factory=list)
    uptime_ms: int = 0
    battery_voltage: float = 0.0
    raw_data: dict = field(default_factory=dict)


class TelemetryService:
    """
    Service for managing telemetry subscriptions and data.

    Subscribes to telemetry topics from the robot and provides
    a clean interface for accessing latest values or historical data.

    Example:
        telem = TelemetryService(client)

        # Subscribe to updates
        telem.on_imu(lambda data: print(f"IMU: {data.ax}"))

        # Start receiving telemetry
        await telem.start()

        # Get latest values
        imu = telem.get_latest_imu()
        snapshot = telem.get_snapshot()

        # Stop when done
        telem.stop()
    """

    def __init__(
        self,
        client: "MaraClient",
        history_size: int = 200,
    ):
        """
        Initialize telemetry service.

        Args:
            client: Connected MaraClient instance
            history_size: Number of telemetry samples to keep in history
        """
        self.client = client
        self._history_size = history_size

        # Latest values
        self._latest_imu: Optional[ImuData] = None
        self._latest_encoders: dict[int, EncoderData] = {}
        self._latest_motors: dict[int, MotorData] = {}
        self._latest_state: str = "UNKNOWN"
        self._latest_timestamp: float = 0.0

        # History buffers
        self._imu_history: deque[ImuData] = deque(maxlen=history_size)
        self._encoder_history: dict[int, deque[EncoderData]] = {}

        # Callbacks
        self._imu_callbacks: list[Callable[[ImuData], None]] = []
        self._encoder_callbacks: list[Callable[[EncoderData], None]] = []
        self._state_callbacks: list[Callable[[str], None]] = []
        self._raw_callbacks: list[Callable[[dict], None]] = []

        # Subscribed state
        self._subscribed = False

    async def start(self, interval_ms: int = 50) -> None:
        """
        Start telemetry subscription.

        Args:
            interval_ms: Telemetry interval in milliseconds
        """
        if self._subscribed:
            return

        # Set telemetry interval
        await self.client.send_reliable(
            "CMD_TELEM_SET_INTERVAL",
            {"interval_ms": interval_ms},
        )

        # Subscribe to topics
        self.client.bus.subscribe("telemetry.binary", self._on_binary_telemetry)
        self.client.bus.subscribe("telemetry", self._on_json_telemetry)
        self.client.bus.subscribe("state.changed", self._on_state_changed)

        self._subscribed = True

    def stop(self) -> None:
        """Stop telemetry subscription."""
        if not self._subscribed:
            return

        self.client.bus.unsubscribe("telemetry.binary", self._on_binary_telemetry)
        self.client.bus.unsubscribe("telemetry", self._on_json_telemetry)
        self.client.bus.unsubscribe("state.changed", self._on_state_changed)

        self._subscribed = False

    # -------------------------------------------------------------------------
    # Callback registration
    # -------------------------------------------------------------------------

    def on_imu(self, callback: Callable[[ImuData], None]) -> None:
        """Register callback for IMU updates."""
        self._imu_callbacks.append(callback)

    def on_encoder(self, callback: Callable[[EncoderData], None]) -> None:
        """Register callback for encoder updates."""
        self._encoder_callbacks.append(callback)

    def on_state(self, callback: Callable[[str], None]) -> None:
        """Register callback for state changes."""
        self._state_callbacks.append(callback)

    def on_raw(self, callback: Callable[[dict], None]) -> None:
        """Register callback for raw telemetry data."""
        self._raw_callbacks.append(callback)

    def remove_callback(self, callback: Callable) -> None:
        """Remove a registered callback."""
        for cb_list in [
            self._imu_callbacks,
            self._encoder_callbacks,
            self._state_callbacks,
            self._raw_callbacks,
        ]:
            if callback in cb_list:
                cb_list.remove(callback)

    # -------------------------------------------------------------------------
    # Data access
    # -------------------------------------------------------------------------

    def get_latest_imu(self) -> Optional[ImuData]:
        """Get most recent IMU data."""
        return self._latest_imu

    def get_latest_encoder(self, encoder_id: int) -> Optional[EncoderData]:
        """Get most recent encoder data for given ID."""
        return self._latest_encoders.get(encoder_id)

    def get_all_encoders(self) -> dict[int, EncoderData]:
        """Get all latest encoder data."""
        return self._latest_encoders.copy()

    def get_latest_motor(self, motor_id: int) -> Optional[MotorData]:
        """Get most recent motor data for given ID."""
        return self._latest_motors.get(motor_id)

    def get_state(self) -> str:
        """Get current robot state."""
        return self._latest_state

    def get_snapshot(self) -> TelemetrySnapshot:
        """Get complete telemetry snapshot."""
        return TelemetrySnapshot(
            timestamp=self._latest_timestamp,
            state=self._latest_state,
            imu=self._latest_imu,
            encoders=list(self._latest_encoders.values()),
            motors=list(self._latest_motors.values()),
        )

    def get_imu_history(self, count: Optional[int] = None) -> list[ImuData]:
        """
        Get IMU history.

        Args:
            count: Number of samples (None = all)

        Returns:
            List of IMU samples (oldest first)
        """
        if count is None:
            return list(self._imu_history)
        return list(self._imu_history)[-count:]

    def get_encoder_history(
        self,
        encoder_id: int,
        count: Optional[int] = None,
    ) -> list[EncoderData]:
        """
        Get encoder history.

        Args:
            encoder_id: Encoder ID
            count: Number of samples (None = all)

        Returns:
            List of encoder samples (oldest first)
        """
        history = self._encoder_history.get(encoder_id, deque())
        if count is None:
            return list(history)
        return list(history)[-count:]

    # -------------------------------------------------------------------------
    # Internal handlers
    # -------------------------------------------------------------------------

    def _on_binary_telemetry(self, packet: Any) -> None:
        """Handle binary telemetry packet."""
        self._latest_timestamp = time.time()

        # Parse IMU data
        if hasattr(packet, "imu"):
            imu_data = ImuData(
                ax=getattr(packet.imu, "ax", 0.0),
                ay=getattr(packet.imu, "ay", 0.0),
                az=getattr(packet.imu, "az", 0.0),
                gx=getattr(packet.imu, "gx", 0.0),
                gy=getattr(packet.imu, "gy", 0.0),
                gz=getattr(packet.imu, "gz", 0.0),
                timestamp=self._latest_timestamp,
            )
            self._latest_imu = imu_data
            self._imu_history.append(imu_data)

            for cb in self._imu_callbacks:
                try:
                    cb(imu_data)
                except Exception:
                    pass

        # Parse encoder data
        if hasattr(packet, "encoders"):
            for i, enc in enumerate(packet.encoders):
                enc_data = EncoderData(
                    encoder_id=i,
                    ticks=getattr(enc, "ticks", 0),
                    velocity=getattr(enc, "velocity", 0.0),
                    timestamp=self._latest_timestamp,
                )
                self._latest_encoders[i] = enc_data

                if i not in self._encoder_history:
                    self._encoder_history[i] = deque(maxlen=self._history_size)
                self._encoder_history[i].append(enc_data)

                for cb in self._encoder_callbacks:
                    try:
                        cb(enc_data)
                    except Exception:
                        pass

        # State
        if hasattr(packet, "state"):
            new_state = str(packet.state)
            if new_state != self._latest_state:
                self._latest_state = new_state
                for cb in self._state_callbacks:
                    try:
                        cb(new_state)
                    except Exception:
                        pass

    def _on_json_telemetry(self, data: dict) -> None:
        """Handle JSON telemetry packet."""
        self._latest_timestamp = time.time()

        # Notify raw callbacks
        for cb in self._raw_callbacks:
            try:
                cb(data)
            except Exception:
                pass

        # Parse IMU data
        if "imu" in data:
            imu_dict = data["imu"]
            imu_data = ImuData.from_dict(imu_dict)
            imu_data.timestamp = self._latest_timestamp
            self._latest_imu = imu_data
            self._imu_history.append(imu_data)

            for cb in self._imu_callbacks:
                try:
                    cb(imu_data)
                except Exception:
                    pass

        # Parse encoder data
        for key in data:
            if key.startswith("encoder"):
                try:
                    encoder_id = int(key.replace("encoder", ""))
                    enc_dict = data[key]
                    enc_data = EncoderData.from_dict(encoder_id, enc_dict)
                    enc_data.timestamp = self._latest_timestamp
                    self._latest_encoders[encoder_id] = enc_data

                    if encoder_id not in self._encoder_history:
                        self._encoder_history[encoder_id] = deque(
                            maxlen=self._history_size
                        )
                    self._encoder_history[encoder_id].append(enc_data)

                    for cb in self._encoder_callbacks:
                        try:
                            cb(enc_data)
                        except Exception:
                            pass
                except (ValueError, KeyError):
                    pass

        # State
        if "state" in data:
            new_state = data["state"]
            if new_state != self._latest_state:
                self._latest_state = new_state
                for cb in self._state_callbacks:
                    try:
                        cb(new_state)
                    except Exception:
                        pass

    def _on_state_changed(self, data: dict) -> None:
        """Handle state change event."""
        new_state = data.get("state", "UNKNOWN")
        if new_state != self._latest_state:
            self._latest_state = new_state
            for cb in self._state_callbacks:
                try:
                    cb(new_state)
                except Exception:
                    pass
