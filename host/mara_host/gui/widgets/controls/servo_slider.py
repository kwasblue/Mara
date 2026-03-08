# mara_host/gui/widgets/controls/servo_slider.py
"""
Servo slider widget.

Provides a slider for controlling servo angle with labels and units.
"""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QSlider,
)
from PySide6.QtCore import Qt, Signal


class ServoSliderGroup(QWidget):
    """
    Servo angle slider with label and value display.

    Emits:
        value_changed: (servo_id: int, angle: float) when slider moves
        released: (servo_id: int, angle: float) when slider is released

    Example:
        slider = ServoSliderGroup(servo_id=0)
        slider.value_changed.connect(lambda sid, angle: print(f"S{sid}: {angle}"))
        slider.released.connect(lambda sid, angle: print(f"S{sid} final: {angle}"))
    """

    value_changed = Signal(int, float)  # servo_id, angle (0-180)
    released = Signal(int, float)  # servo_id, final angle

    def __init__(
        self,
        servo_id: int,
        label: str = "",
        min_angle: int = 0,
        max_angle: int = 180,
        initial_angle: int = 90,
        parent=None,
    ):
        """
        Initialize servo slider.

        Args:
            servo_id: Servo ID (0-7)
            label: Custom label (default: "S{servo_id}")
            min_angle: Minimum angle
            max_angle: Maximum angle
            initial_angle: Initial angle
            parent: Parent widget
        """
        super().__init__(parent)

        self.servo_id = servo_id
        self._min = min_angle
        self._max = max_angle

        self._setup_ui(label or f"S{servo_id}", initial_angle)

    def _setup_ui(self, label: str, initial_angle: int) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Label
        self._label = QLabel(label)
        self._label.setMinimumWidth(24)
        self._label.setStyleSheet("color: #71717A; font-size: 12px;")
        layout.addWidget(self._label)

        # Slider
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(self._min, self._max)
        self._slider.setValue(initial_angle)
        self._slider.valueChanged.connect(self._on_value_changed)
        self._slider.sliderReleased.connect(self._on_released)
        layout.addWidget(self._slider, 1)

        # Value display
        self._value_label = QLabel(str(initial_angle))
        self._value_label.setMinimumWidth(36)
        self._value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._value_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "color: #FAFAFA; "
            "font-size: 12px;"
        )
        layout.addWidget(self._value_label)

        # Unit
        unit = QLabel("deg")
        unit.setStyleSheet("color: #52525B; font-size: 11px;")
        layout.addWidget(unit)

    def _on_value_changed(self, value: int) -> None:
        """Handle slider value change."""
        self._value_label.setText(str(value))
        self.value_changed.emit(self.servo_id, float(value))

    def _on_released(self) -> None:
        """Handle slider release."""
        self.released.emit(self.servo_id, float(self._slider.value()))

    def value(self) -> int:
        """Get current slider value (angle)."""
        return self._slider.value()

    def setValue(self, value: int) -> None:
        """Set slider value (angle)."""
        self._slider.setValue(value)

    def angle(self) -> float:
        """Get angle as float."""
        return float(self._slider.value())

    def setRange(self, min_angle: int, max_angle: int) -> None:
        """Set angle range."""
        self._min = min_angle
        self._max = max_angle
        self._slider.setRange(min_angle, max_angle)

    def center(self) -> None:
        """Move to center position."""
        center = (self._min + self._max) // 2
        self.setValue(center)

    def setEnabled(self, enabled: bool) -> None:
        """Enable/disable the slider."""
        self._slider.setEnabled(enabled)
        super().setEnabled(enabled)
