# mara_host/gui/widgets/video_display.py
"""
Video display widget for camera feeds.
"""

from typing import Optional
import time

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class VideoDisplayWidget(QWidget):
    """
    Widget for displaying video frames.

    Features:
    - Displays numpy arrays (BGR) or QImage
    - Maintains aspect ratio
    - Shows FPS overlay
    - Placeholder when no frames
    """

    # Emitted when widget is clicked
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._last_frame_time = 0.0
        self._fps = 0.0
        self._frame_count = 0
        self._fps_update_time = time.time()
        self._show_fps = True

        self._setup_ui()

        # FPS calculation timer
        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.start(1000)  # Update FPS every second

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Video display label
        self._display = QLabel()
        self._display.setAlignment(Qt.AlignCenter)
        self._display.setMinimumSize(320, 240)
        self._display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._display.setStyleSheet(
            "background-color: #111113; "
            "border-radius: 6px;"
        )

        # Placeholder text
        self._display.setText("No video feed")
        self._display.setStyleSheet(
            "background-color: #111113; "
            "color: #52525B; "
            "font-size: 14px; "
            "border-radius: 6px;"
        )

        layout.addWidget(self._display)

        # FPS overlay label
        self._fps_label = QLabel("0 FPS")
        self._fps_label.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.6); "
            "color: #FAFAFA; "
            "font-size: 11px; "
            "font-family: 'Menlo', monospace; "
            "padding: 4px 8px; "
            "border-radius: 4px;"
        )
        self._fps_label.setParent(self._display)
        self._fps_label.move(8, 8)
        self._fps_label.setVisible(self._show_fps)

    def set_frame(self, frame) -> None:
        """
        Display a frame.

        Args:
            frame: numpy array (BGR) or QImage
        """
        if frame is None:
            return

        self._frame_count += 1
        self._last_frame_time = time.time()

        if HAS_NUMPY and isinstance(frame, np.ndarray):
            # Convert BGR numpy array to QImage
            if len(frame.shape) == 3:
                height, width, channels = frame.shape
                if channels == 3:
                    # BGR to RGB
                    rgb = frame[:, :, ::-1].copy()
                    bytes_per_line = 3 * width
                    qimage = QImage(
                        rgb.data, width, height,
                        bytes_per_line, QImage.Format_RGB888
                    )
                elif channels == 4:
                    # BGRA to RGBA
                    rgba = frame[:, :, [2, 1, 0, 3]].copy()
                    bytes_per_line = 4 * width
                    qimage = QImage(
                        rgba.data, width, height,
                        bytes_per_line, QImage.Format_RGBA8888
                    )
                else:
                    return
            elif len(frame.shape) == 2:
                # Grayscale
                height, width = frame.shape
                qimage = QImage(
                    frame.data, width, height,
                    width, QImage.Format_Grayscale8
                )
            else:
                return
        elif isinstance(frame, QImage):
            qimage = frame
        else:
            return

        # Scale to fit while maintaining aspect ratio
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            self._display.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self._display.setPixmap(scaled)
        self._display.setText("")  # Clear placeholder text

    def set_placeholder(self, text: str) -> None:
        """Set placeholder text when no video."""
        self._display.clear()
        self._display.setText(text)

    def _update_fps(self) -> None:
        """Update FPS calculation."""
        now = time.time()
        elapsed = now - self._fps_update_time

        if elapsed > 0:
            self._fps = self._frame_count / elapsed

        self._frame_count = 0
        self._fps_update_time = now

        if self._show_fps:
            self._fps_label.setText(f"{self._fps:.1f} FPS")

    def set_show_fps(self, show: bool) -> None:
        """Toggle FPS overlay visibility."""
        self._show_fps = show
        self._fps_label.setVisible(show)

    @property
    def fps(self) -> float:
        """Get current FPS."""
        return self._fps

    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        self.clicked.emit()
        super().mousePressEvent(event)

    def resizeEvent(self, event) -> None:
        """Handle resize to reposition FPS label."""
        super().resizeEvent(event)
        # Keep FPS label in top-left corner
        self._fps_label.move(8, 8)
