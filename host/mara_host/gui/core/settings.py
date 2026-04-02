# mara_host/gui/core/settings.py
"""
GUI settings persistence using QSettings.

Provides a type-safe wrapper around QSettings for
storing and retrieving application preferences.
"""

from typing import Optional, Any, List
from PySide6.QtCore import QSettings

from mara_host.core._generated_config import DEFAULT_BAUD_RATE


class GuiSettings:
    """
    Settings wrapper for persistent GUI configuration.

    Uses QSettings for cross-platform persistence.

    Example:
        settings = GuiSettings()

        # Save settings
        settings.set_last_port("/dev/cu.usbserial-0001")
        settings.set_window_geometry(window.saveGeometry())

        # Load settings
        port = settings.get_last_port()
        geometry = settings.get_window_geometry()
    """

    def __init__(self):
        self._settings = QSettings("MARA", "MaraHost")

    # ==================== Connection Settings ====================

    def get_last_port(self) -> str:
        """Get last used serial port."""
        return self._settings.value("connection/last_port", "", type=str)

    def set_last_port(self, port: str) -> None:
        """Set last used serial port."""
        self._settings.setValue("connection/last_port", port)

    def get_last_host(self) -> str:
        """Get last used TCP host."""
        return self._settings.value("connection/last_host", "192.168.4.1", type=str)

    def set_last_host(self, host: str) -> None:
        """Set last used TCP host."""
        self._settings.setValue("connection/last_host", host)

    def get_last_tcp_port(self) -> int:
        """Get last used TCP port."""
        return self._settings.value("connection/last_tcp_port", 3333, type=int)

    def set_last_tcp_port(self, port: int) -> None:
        """Set last used TCP port."""
        self._settings.setValue("connection/last_tcp_port", port)

    def get_transport_type(self) -> str:
        """Get last used transport type."""
        return self._settings.value("connection/transport_type", "serial", type=str)

    def set_transport_type(self, transport_type: str) -> None:
        """Set last used transport type."""
        self._settings.setValue("connection/transport_type", transport_type)

    def get_baudrate(self) -> int:
        """Get last used baudrate."""
        return self._settings.value("connection/baudrate", DEFAULT_BAUD_RATE, type=int)

    def set_baudrate(self, baudrate: int) -> None:
        """Set last used baudrate."""
        self._settings.setValue("connection/baudrate", baudrate)

    def get_recent_ports(self) -> List[str]:
        """Get list of recently used ports."""
        return self._settings.value("connection/recent_ports", [], type=list)

    def add_recent_port(self, port: str) -> None:
        """Add a port to recent ports list."""
        recent = self.get_recent_ports()
        if port in recent:
            recent.remove(port)
        recent.insert(0, port)
        recent = recent[:10]  # Keep max 10
        self._settings.setValue("connection/recent_ports", recent)

    # ==================== Window Settings ====================

    def get_window_geometry(self) -> Optional[bytes]:
        """Get saved window geometry."""
        return self._settings.value("window/geometry", None)

    def set_window_geometry(self, geometry: bytes) -> None:
        """Save window geometry."""
        self._settings.setValue("window/geometry", geometry)

    def get_window_state(self) -> Optional[bytes]:
        """Get saved window state."""
        return self._settings.value("window/state", None)

    def set_window_state(self, state: bytes) -> None:
        """Save window state."""
        self._settings.setValue("window/state", state)

    def get_last_panel(self) -> str:
        """Get last active panel."""
        return self._settings.value("window/last_panel", "dashboard", type=str)

    def set_last_panel(self, panel: str) -> None:
        """Set last active panel."""
        self._settings.setValue("window/last_panel", panel)

    # ==================== Telemetry Settings ====================

    def get_telemetry_interval(self) -> int:
        """Get telemetry interval in ms."""
        return self._settings.value("telemetry/interval_ms", 50, type=int)

    def set_telemetry_interval(self, interval_ms: int) -> None:
        """Set telemetry interval in ms."""
        self._settings.setValue("telemetry/interval_ms", interval_ms)

    def get_plot_history_size(self) -> int:
        """Get number of telemetry samples to keep for plotting."""
        return self._settings.value("telemetry/plot_history", 200, type=int)

    def set_plot_history_size(self, size: int) -> None:
        """Set plot history size."""
        self._settings.setValue("telemetry/plot_history", size)

    # ==================== Camera Settings ====================

    def get_camera_url(self) -> str:
        """Get camera base URL."""
        return self._settings.value("camera/url", "http://10.0.0.60", type=str)

    def set_camera_url(self, url: str) -> None:
        """Set camera base URL."""
        self._settings.setValue("camera/url", url)

    def get_camera_resolution(self) -> int:
        """Get camera resolution index."""
        return self._settings.value("camera/resolution", 8, type=int)  # VGA

    def set_camera_resolution(self, resolution: int) -> None:
        """Set camera resolution."""
        self._settings.setValue("camera/resolution", resolution)

    # ==================== Recording Settings ====================

    def get_recording_dir(self) -> str:
        """Get recording output directory."""
        return self._settings.value("recording/directory", "recordings", type=str)

    def set_recording_dir(self, directory: str) -> None:
        """Set recording output directory."""
        self._settings.setValue("recording/directory", directory)

    # ==================== Velocity Limits ====================

    def get_max_linear_velocity(self) -> float:
        """Get maximum linear velocity limit."""
        return self._settings.value("control/max_linear", 1.0, type=float)

    def set_max_linear_velocity(self, max_vel: float) -> None:
        """Set maximum linear velocity limit."""
        self._settings.setValue("control/max_linear", max_vel)

    def get_max_angular_velocity(self) -> float:
        """Get maximum angular velocity limit."""
        return self._settings.value("control/max_angular", 2.0, type=float)

    def set_max_angular_velocity(self, max_vel: float) -> None:
        """Set maximum angular velocity limit."""
        self._settings.setValue("control/max_angular", max_vel)

    # ==================== Generic Access ====================

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.value(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        self._settings.setValue(key, value)

    def sync(self) -> None:
        """Force sync settings to disk."""
        self._settings.sync()
