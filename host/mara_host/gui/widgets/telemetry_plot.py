# mara_host/gui/widgets/telemetry_plot.py
"""
Real-time telemetry plotting widget using pyqtgraph.
"""

import sys
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
import time

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QSizePolicy, QCheckBox
from PySide6.QtCore import QTimer, QSize

try:
    import pyqtgraph as pg
    # Configure once globally. On Linux, OpenGL via Mesa/NVIDIA can segfault;
    # software rendering is stable and fast enough for our telemetry rates.
    pg.setConfigOptions(
        antialias=True,
        useOpenGL=False,
        background="#111113",
        foreground="#A1A1AA",
    )
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False


@dataclass
class DataSeries:
    """A single data series for plotting."""
    name: str
    color: str
    data: deque = field(default_factory=lambda: deque(maxlen=200))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=200))
    plot_item: Optional[object] = None
    visible: bool = True
    checkbox: Optional[object] = None


class TelemetryPlotWidget(QWidget):
    """
    Real-time telemetry plotting widget.

    Features:
    - Multiple data series with different colors
    - Rolling window (configurable)
    - Auto-scaling Y axis
    - Pause/resume
    - Configurable update rate
    """

    # Color palette for plot lines
    COLORS = [
        "#3B82F6",  # Blue
        "#EF4444",  # Red
        "#22C55E",  # Green
        "#F59E0B",  # Amber
        "#8B5CF6",  # Purple
        "#06B6D4",  # Cyan
    ]

    def __init__(self, title: str = "Telemetry", parent=None):
        super().__init__(parent)

        self._title = title
        self._series: dict[str, DataSeries] = {}
        self._paused = False
        self._window_size = 200  # Number of points
        self._start_time = time.time()

        self._setup_ui()

        # Update timer - 30fps
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_plot)
        self._update_timer.start(33)  # ~30fps

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Set size policy to expand
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(120)

        if not HAS_PYQTGRAPH:
            # Fallback if pyqtgraph not installed
            label = QLabel("pyqtgraph not installed\npip install pyqtgraph")
            label.setStyleSheet(
                "background-color: #1F1F23; "
                "color: #71717A; "
                "padding: 40px; "
                "border-radius: 6px;"
            )
            layout.addWidget(label)
            return

        # Create plot widget
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setMinimumHeight(100)
        self._plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Compact title and labels
        self._plot_widget.setTitle(self._title, color="#71717A", size="10pt")
        self._plot_widget.showGrid(x=True, y=True, alpha=0.15)

        # Hide axis labels to save space, keep tick marks
        self._plot_widget.getPlotItem().getAxis('bottom').setHeight(20)
        self._plot_widget.getPlotItem().getAxis('left').setWidth(40)

        # Style the plot
        self._plot_widget.getPlotItem().getViewBox().setBackgroundColor("#111113")

        # Add legend
        self._plot_widget.addLegend(offset=(5, 5), labelTextSize='9pt')

        layout.addWidget(self._plot_widget, 1)

        # Compact controls bar
        controls = QHBoxLayout()
        controls.setSpacing(6)
        controls.setContentsMargins(0, 0, 0, 0)

        # Series toggles container (will be populated when series are added)
        self._toggles_layout = QHBoxLayout()
        self._toggles_layout.setSpacing(8)
        controls.addLayout(self._toggles_layout)

        controls.addStretch()

        # Window size selector
        self._window_combo = QComboBox()
        self._window_combo.addItems(["5s", "10s", "30s", "60s"])
        self._window_combo.setCurrentText("10s")
        self._window_combo.setFixedWidth(55)
        self._window_combo.setFixedHeight(22)
        self._window_combo.currentTextChanged.connect(self._on_window_changed)
        controls.addWidget(self._window_combo)

        # Pause button - smaller
        self._pause_btn = QPushButton("||")
        self._pause_btn.setObjectName("flat")
        self._pause_btn.setFixedHeight(22)
        self._pause_btn.setFixedWidth(28)
        self._pause_btn.setToolTip("Pause/Resume")
        self._pause_btn.clicked.connect(self._toggle_pause)
        controls.addWidget(self._pause_btn)

        # Clear button - smaller
        clear_btn = QPushButton("C")
        clear_btn.setObjectName("flat")
        clear_btn.setFixedHeight(22)
        clear_btn.setFixedWidth(28)
        clear_btn.setToolTip("Clear data")
        clear_btn.clicked.connect(self.clear)
        controls.addWidget(clear_btn)

        layout.addLayout(controls)

    def sizeHint(self) -> QSize:
        """Provide a reasonable size hint."""
        return QSize(400, 150)

    def add_series(self, name: str, color: Optional[str] = None) -> None:
        """Add a data series to the plot."""
        if not HAS_PYQTGRAPH:
            return

        if name in self._series:
            return

        # Auto-assign color
        if color is None:
            color = self.COLORS[len(self._series) % len(self.COLORS)]

        series = DataSeries(name=name, color=color)

        # Create plot line
        pen = pg.mkPen(color=color, width=2)
        series.plot_item = self._plot_widget.plot([], [], pen=pen, name=name)

        # Create toggle checkbox
        checkbox = QCheckBox(name)
        checkbox.setChecked(True)
        checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {color};
                font-size: 10px;
                spacing: 3px;
            }}
            QCheckBox::indicator {{
                width: 12px;
                height: 12px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {color};
                border: 1px solid {color};
                border-radius: 2px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: transparent;
                border: 1px solid #52525B;
                border-radius: 2px;
            }}
        """)
        checkbox.toggled.connect(lambda checked, n=name: self._on_series_toggled(n, checked))
        series.checkbox = checkbox

        if hasattr(self, '_toggles_layout'):
            self._toggles_layout.addWidget(checkbox)

        self._series[name] = series

    def _on_series_toggled(self, name: str, visible: bool) -> None:
        """Handle series visibility toggle."""
        if name in self._series:
            series = self._series[name]
            series.visible = visible
            if series.plot_item:
                series.plot_item.setVisible(visible)

    def add_point(self, series_name: str, value: float, timestamp: Optional[float] = None) -> None:
        """Add a data point to a series."""
        if series_name not in self._series:
            self.add_series(series_name)

        if timestamp is None:
            timestamp = time.time() - self._start_time

        series = self._series[series_name]
        series.data.append(value)
        series.timestamps.append(timestamp)

    def add_points(self, data: dict[str, float], timestamp: Optional[float] = None) -> None:
        """Add multiple data points at once."""
        if timestamp is None:
            timestamp = time.time() - self._start_time

        for name, value in data.items():
            self.add_point(name, value, timestamp)

    def _update_plot(self) -> None:
        """Update the plot display."""
        if not HAS_PYQTGRAPH or self._paused:
            return

        for series in self._series.values():
            if series.plot_item and len(series.data) > 0 and series.visible:
                series.plot_item.setData(
                    list(series.timestamps),
                    list(series.data)
                )

    def _on_window_changed(self, text: str) -> None:
        """Handle window size change."""
        # Parse seconds from text
        seconds = int(text.rstrip("s"))
        # Assuming ~30 samples/sec
        self._window_size = seconds * 30

        # Update deque max lengths
        for series in self._series.values():
            old_data = list(series.data)
            old_ts = list(series.timestamps)
            series.data = deque(old_data[-self._window_size:], maxlen=self._window_size)
            series.timestamps = deque(old_ts[-self._window_size:], maxlen=self._window_size)

    def _toggle_pause(self) -> None:
        """Toggle pause state."""
        self._paused = not self._paused
        self._pause_btn.setText(">" if self._paused else "||")
        self._pause_btn.setToolTip("Resume" if self._paused else "Pause")

    def clear(self) -> None:
        """Clear all data."""
        self._start_time = time.time()
        for series in self._series.values():
            series.data.clear()
            series.timestamps.clear()
            if series.plot_item:
                series.plot_item.setData([], [])

    def set_paused(self, paused: bool) -> None:
        """Set pause state."""
        self._paused = paused
        if hasattr(self, '_pause_btn'):
            self._pause_btn.setText(">" if paused else "||")
            self._pause_btn.setToolTip("Resume" if paused else "Pause")

    def showEvent(self, event) -> None:
        """Resume the update timer when the widget becomes visible."""
        super().showEvent(event)
        if hasattr(self, '_update_timer') and not self._paused:
            self._update_timer.start(33)

    def hideEvent(self, event) -> None:
        """Stop the update timer when the widget is hidden to save CPU."""
        super().hideEvent(event)
        if hasattr(self, '_update_timer'):
            self._update_timer.stop()


class ImuPlotWidget(TelemetryPlotWidget):
    """Pre-configured plot widget for IMU data."""

    def __init__(self, parent=None):
        super().__init__(title="IMU", parent=parent)

        # Add accelerometer series
        self.add_series("ax", "#3B82F6")  # Blue
        self.add_series("ay", "#22C55E")  # Green
        self.add_series("az", "#EF4444")  # Red

    def update_imu(self, imu_data) -> None:
        """Update with IMU data object."""
        self.add_points({
            "ax": getattr(imu_data, "ax", 0),
            "ay": getattr(imu_data, "ay", 0),
            "az": getattr(imu_data, "az", 0),
        })


class GyroPlotWidget(TelemetryPlotWidget):
    """Pre-configured plot widget for gyroscope data."""

    def __init__(self, parent=None):
        super().__init__(title="Gyroscope", parent=parent)

        self.add_series("gx", "#F59E0B")  # Amber
        self.add_series("gy", "#8B5CF6")  # Purple
        self.add_series("gz", "#06B6D4")  # Cyan

    def update_gyro(self, imu_data) -> None:
        """Update with gyro data from IMU object."""
        self.add_points({
            "gx": getattr(imu_data, "gx", 0),
            "gy": getattr(imu_data, "gy", 0),
            "gz": getattr(imu_data, "gz", 0),
        })


class EncoderPlotWidget(TelemetryPlotWidget):
    """Pre-configured plot widget for encoder data."""

    def __init__(self, num_encoders: int = 2, parent=None):
        super().__init__(title="Encoders", parent=parent)

        for i in range(num_encoders):
            self.add_series(f"enc{i}")

    def update_encoder(self, encoder_id: int, value: int) -> None:
        """Update a single encoder value."""
        self.add_point(f"enc{encoder_id}", value)


class MotorPlotWidget(TelemetryPlotWidget):
    """Pre-configured plot widget for motor speeds."""

    def __init__(self, num_motors: int = 2, parent=None):
        super().__init__(title="Motors", parent=parent)

        for i in range(num_motors):
            self.add_series(f"motor{i}")

    def update_motor(self, motor_id: int, speed: float) -> None:
        """Update a single motor speed."""
        self.add_point(f"motor{motor_id}", speed)
