# mara_host/gui/widgets/controls/motor_slider.py
"""
Motor slider widget.

Provides a slider for controlling DC motor speed with labels and units.
"""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QSlider,
)
from PySide6.QtCore import Qt, Signal


class MotorSliderGroup(QWidget):
    """
    Motor speed slider with label and value display.

    Emits:
        value_changed: (motor_id: int, speed: float) when slider moves
        released: (motor_id: int) when slider is released

    Example:
        slider = MotorSliderGroup(motor_id=0)
        slider.value_changed.connect(lambda mid, speed: print(f"M{mid}: {speed}"))
        slider.released.connect(lambda mid: print(f"M{mid} released"))
    """

    value_changed = Signal(int, float)  # motor_id, speed (-1.0 to 1.0)
    released = Signal(int)  # motor_id

    def __init__(
        self,
        motor_id: int,
        label: str = "",
        min_value: int = -100,
        max_value: int = 100,
        initial_value: int = 0,
        auto_zero: bool = True,
        parent=None,
    ):
        """
        Initialize motor slider.

        Args:
            motor_id: Motor ID (0-3)
            label: Custom label (default: "M{motor_id}")
            min_value: Minimum slider value
            max_value: Maximum slider value
            initial_value: Initial slider position
            auto_zero: Auto-zero on release
            parent: Parent widget
        """
        super().__init__(parent)

        self.motor_id = motor_id
        self._auto_zero = auto_zero
        self._min = min_value
        self._max = max_value

        self._setup_ui(label or f"M{motor_id}", initial_value)

    def _setup_ui(self, label: str, initial_value: int) -> None:
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
        self._slider.setValue(initial_value)
        self._slider.valueChanged.connect(self._on_value_changed)
        self._slider.sliderReleased.connect(self._on_released)
        layout.addWidget(self._slider, 1)

        # Value display
        self._value_label = QLabel(str(initial_value))
        self._value_label.setMinimumWidth(36)
        self._value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._value_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "color: #FAFAFA; "
            "font-size: 12px;"
        )
        layout.addWidget(self._value_label)

        # Unit
        unit = QLabel("%")
        unit.setStyleSheet("color: #52525B; font-size: 11px;")
        layout.addWidget(unit)

    def _on_value_changed(self, value: int) -> None:
        """Handle slider value change."""
        self._value_label.setText(str(value))
        # Convert to -1.0 to 1.0 range
        speed = value / 100.0
        self.value_changed.emit(self.motor_id, speed)

    def _on_released(self) -> None:
        """Handle slider release."""
        if self._auto_zero:
            self._slider.setValue(0)
        self.released.emit(self.motor_id)

    def value(self) -> int:
        """Get current slider value."""
        return self._slider.value()

    def setValue(self, value: int) -> None:
        """Set slider value."""
        self._slider.setValue(value)

    def speed(self) -> float:
        """Get speed as float (-1.0 to 1.0)."""
        return self._slider.value() / 100.0

    def setEnabled(self, enabled: bool) -> None:
        """Enable/disable the slider."""
        self._slider.setEnabled(enabled)
        super().setEnabled(enabled)
