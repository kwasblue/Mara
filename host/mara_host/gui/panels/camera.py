# mara_host/gui/panels/camera.py
"""
Camera panel for MJPEG video streaming and control.
"""

from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QSlider,
    QCheckBox,
    QFormLayout,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QImage, QPixmap

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class VideoDisplay(QWidget):
    """
    Widget for displaying video frames.

    Converts numpy arrays (BGR) to QImage and displays them.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._pixmap: Optional[QPixmap] = None
        self._aspect_ratio = 4 / 3

        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #1E1E2E; border-radius: 8px;")

        # Layout with centered label
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("color: #707090;")
        self.image_label.setText("No video feed")
        layout.addWidget(self.image_label)

    def set_frame(self, frame: Any) -> None:
        """
        Set the current frame to display.

        Args:
            frame: numpy array in BGR format (from OpenCV)
        """
        if not HAS_NUMPY or frame is None:
            return

        try:
            height, width, channels = frame.shape

            # Convert BGR to RGB
            if channels == 3:
                rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])
            else:
                rgb_frame = frame

            # Create QImage
            bytes_per_line = 3 * width
            qimg = QImage(
                rgb_frame.data,
                width,
                height,
                bytes_per_line,
                QImage.Format_RGB888,
            )

            # Scale to fit while maintaining aspect ratio
            self._pixmap = QPixmap.fromImage(qimg)
            self._update_display()

        except Exception:
            pass

    def _update_display(self) -> None:
        """Update the displayed image."""
        if self._pixmap is None:
            return

        # Scale to fit the label while maintaining aspect ratio
        scaled = self._pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        """Handle resize to update scaled image."""
        super().resizeEvent(event)
        self._update_display()

    def clear(self) -> None:
        """Clear the display."""
        self._pixmap = None
        self.image_label.clear()
        self.image_label.setText("No video feed")


class CameraPanel(QWidget):
    """
    Camera panel for viewing and controlling camera stream.

    Layout:
        ┌────────────────────────────┬────────────────────────────┐
        │ ┌────────────────────────┐ │ Settings                   │
        │ │                        │ │ URL: [http://10.0.0.60]   │
        │ │    MJPEG Video Feed    │ │ Resolution: [VGA ▼]       │
        │ │                        │ │ Quality: [===10===]       │
        │ │   FPS: 15 | Lat: 45ms  │ │ Brightness: [=====]       │
        │ └────────────────────────┘ │ [✓] Flash                 │
        │                            ├────────────────────────────┤
        │                            │ [Snapshot] [Record]        │
        └────────────────────────────┴────────────────────────────┘
    """

    def __init__(
        self,
        signals: GuiSignals,
        controller: RobotController,
        settings: GuiSettings,
    ):
        super().__init__()

        self.signals = signals
        self.controller = controller
        self.settings = settings

        self._stream_service = None
        self._connected = False
        self._recording = False

        self._setup_ui()
        self._setup_timers()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the camera panel UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Left side - video display
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(8)

        # Video display
        self.video_display = VideoDisplay()
        video_layout.addWidget(self.video_display, 1)

        # Stats bar
        stats_layout = QHBoxLayout()

        self.fps_label = QLabel("FPS: --")
        self.fps_label.setStyleSheet("color: #71717A; font-size: 11px;")
        stats_layout.addWidget(self.fps_label)

        stats_layout.addStretch()

        self.resolution_label = QLabel("--x--")
        self.resolution_label.setStyleSheet("color: #71717A; font-size: 11px;")
        stats_layout.addWidget(self.resolution_label)

        stats_layout.addStretch()

        self.bandwidth_label = QLabel("-- KB/s")
        self.bandwidth_label.setStyleSheet("color: #71717A; font-size: 11px;")
        stats_layout.addWidget(self.bandwidth_label)

        video_layout.addLayout(stats_layout)

        layout.addWidget(video_container, 2)

        # Right side - controls
        controls_container = QWidget()
        controls_container.setFixedWidth(280)
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(16)

        # Connection group
        conn_group = QGroupBox("Connection")
        conn_layout = QFormLayout(conn_group)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://10.0.0.60")
        conn_layout.addRow("Camera URL:", self.url_input)

        btn_layout = QHBoxLayout()

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connection)
        btn_layout.addWidget(self.connect_btn)

        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #707090; font-size: 20px;")
        btn_layout.addWidget(self.status_indicator)

        conn_layout.addRow(btn_layout)

        controls_layout.addWidget(conn_group)

        # Settings group
        settings_group = QGroupBox("Settings")
        settings_layout = QFormLayout(settings_group)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "QVGA (320x240)",
            "CIF (400x296)",
            "VGA (640x480)",
            "SVGA (800x600)",
            "XGA (1024x768)",
            "SXGA (1280x1024)",
            "UXGA (1600x1200)",
        ])
        self.resolution_combo.setCurrentIndex(2)  # VGA default
        self.resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        settings_layout.addRow("Resolution:", self.resolution_combo)

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(10, 63)
        self.quality_slider.setValue(10)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        settings_layout.addRow("Quality:", self.quality_slider)

        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(-2, 2)
        self.brightness_slider.setValue(0)
        self.brightness_slider.valueChanged.connect(self._on_brightness_changed)
        settings_layout.addRow("Brightness:", self.brightness_slider)

        self.flash_check = QCheckBox("Enable flash")
        self.flash_check.toggled.connect(self._on_flash_changed)
        settings_layout.addRow(self.flash_check)

        controls_layout.addWidget(settings_group)

        # Actions group
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)

        snapshot_btn = QPushButton("Take Snapshot")
        snapshot_btn.setObjectName("secondary")
        snapshot_btn.clicked.connect(self._take_snapshot)
        actions_layout.addWidget(snapshot_btn)

        self.record_btn = QPushButton("Start Recording")
        self.record_btn.setObjectName("secondary")
        self.record_btn.clicked.connect(self._toggle_recording)
        actions_layout.addWidget(self.record_btn)

        controls_layout.addWidget(actions_group)

        controls_layout.addStretch()

        layout.addWidget(controls_container)

    def _setup_timers(self) -> None:
        """Set up timers for frame updates and stats."""
        # Frame update timer (30 fps target)
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self._update_frame)
        self.frame_timer.setInterval(33)  # ~30 fps

        # Stats update timer (1 Hz)
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.setInterval(1000)

    def _load_settings(self) -> None:
        """Load settings from GUI settings."""
        url = self.settings.get_camera_url()
        if url:
            self.url_input.setText(url)

    def _toggle_connection(self) -> None:
        """Toggle camera connection."""
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self) -> None:
        """Connect to camera stream."""
        url = self.url_input.text().strip()
        if not url:
            url = "http://10.0.0.60"
            self.url_input.setText(url)

        try:
            from mara_host.services.camera import StreamService

            self._stream_service = StreamService(base_url=url)
            self._stream_service.start()

            self._connected = True
            self.connect_btn.setText("Disconnect")
            self.status_indicator.setStyleSheet("color: #22C55E; font-size: 20px;")

            # Start timers
            self.frame_timer.start()
            self.stats_timer.start()

            # Save URL
            self.settings.set_camera_url(url)

            self.signals.status_message.emit(f"Connected to camera: {url}")

        except Exception as e:
            self.signals.status_error.emit(f"Camera connection failed: {e}")
            self.status_indicator.setStyleSheet("color: #EF4444; font-size: 20px;")

    def _disconnect(self) -> None:
        """Disconnect from camera stream."""
        # Stop timers
        self.frame_timer.stop()
        self.stats_timer.stop()

        # Stop stream
        if self._stream_service:
            self._stream_service.stop()
            self._stream_service = None

        self._connected = False
        self.connect_btn.setText("Connect")
        self.status_indicator.setStyleSheet("color: #707090; font-size: 20px;")

        # Clear display
        self.video_display.clear()
        self.fps_label.setText("FPS: --")
        self.resolution_label.setText("--x--")
        self.bandwidth_label.setText("-- KB/s")

        self.signals.status_message.emit("Camera disconnected")

    def _update_frame(self) -> None:
        """Update video frame display."""
        if not self._stream_service:
            return

        frame = self._stream_service.get_frame(timeout=0.01)
        if frame and frame.is_valid:
            self.video_display.set_frame(frame.data)
            self.resolution_label.setText(f"{frame.width}x{frame.height}")

    def _update_stats(self) -> None:
        """Update stream statistics display."""
        if not self._stream_service:
            return

        stats = self._stream_service.get_stats()
        self.fps_label.setText(f"FPS: {stats.fps:.1f}")
        self.bandwidth_label.setText(f"{stats.bytes_per_second / 1024:.1f} KB/s")

    def _on_resolution_changed(self, index: int) -> None:
        """Handle resolution change."""
        resolutions = [
            (320, 240),   # QVGA
            (400, 296),   # CIF
            (640, 480),   # VGA
            (800, 600),   # SVGA
            (1024, 768),  # XGA
            (1280, 1024), # SXGA
            (1600, 1200), # UXGA
        ]

        if self.controller.is_connected and 0 <= index < len(resolutions):
            # Map to framesize (0=QVGA, 1=CIF, etc.)
            self.controller.send_command(
                "CMD_CAM_SET_FRAMESIZE",
                {"framesize": index + 3},  # ESP32-CAM framesize enum offset
                lambda ok, _: None,
            )

    def _on_quality_changed(self, value: int) -> None:
        """Handle quality slider change."""
        if self.controller.is_connected:
            self.controller.send_command(
                "CMD_CAM_SET_QUALITY",
                {"quality": value},
                lambda ok, _: None,
            )

    def _on_brightness_changed(self, value: int) -> None:
        """Handle brightness slider change."""
        if self.controller.is_connected:
            self.controller.send_command(
                "CMD_CAM_SET_BRIGHTNESS",
                {"brightness": value},
                lambda ok, _: None,
            )

    def _on_flash_changed(self, enabled: bool) -> None:
        """Handle flash toggle."""
        if self.controller.is_connected:
            self.controller.send_command(
                "CMD_CAM_FLASH",
                {"enabled": enabled},
                lambda ok, _: None,
            )

    def _take_snapshot(self) -> None:
        """Take a snapshot of the current frame."""
        if not self._stream_service:
            self.signals.status_error.emit("Camera not connected")
            return

        frame = self._stream_service.get_frame(timeout=0.5)
        if frame and frame.is_valid and HAS_NUMPY:
            from PySide6.QtWidgets import QFileDialog
            import cv2

            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Snapshot",
                "snapshot.jpg",
                "JPEG Files (*.jpg);;PNG Files (*.png);;All Files (*)",
            )

            if filename:
                cv2.imwrite(filename, frame.data)
                self.signals.status_message.emit(f"Snapshot saved: {filename}")
        else:
            self.signals.status_error.emit("No frame available")

    def _toggle_recording(self) -> None:
        """Toggle video recording."""
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        """Start video recording."""
        # TODO: Implement video recording
        self._recording = True
        self.record_btn.setText("Stop Recording")
        self.record_btn.setStyleSheet("background-color: #EF4444;")
        self.signals.status_message.emit("Recording started")

    def _stop_recording(self) -> None:
        """Stop video recording."""
        # TODO: Implement video recording
        self._recording = False
        self.record_btn.setText("Start Recording")
        self.record_btn.setStyleSheet("")
        self.signals.status_message.emit("Recording stopped")

    def closeEvent(self, event) -> None:
        """Handle panel close."""
        self._disconnect()
        super().closeEvent(event)
