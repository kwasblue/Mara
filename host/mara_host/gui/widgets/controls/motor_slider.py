# mara_host/gui/widgets/controls/motor_slider.py
"""
Motor slider widget.

Provides a slider for controlling DC motor speed with labels and units.
"""

from PySide6.QtCore import Signal

from .slider_base import RangeSliderWidget


class MotorSliderGroup(RangeSliderWidget):
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
        self._auto_zero = auto_zero

        super().__init__(
            item_id=motor_id,
            label=label or f"M{motor_id}",
            unit="%",
            min_value=min_value,
            max_value=max_value,
            initial_value=initial_value,
            parent=parent,
        )

    @property
    def motor_id(self) -> int:
        """Get motor ID."""
        return self._item_id

    def _on_value_changed(self, value: int) -> None:
        """Handle slider value change."""
        # Convert to -1.0 to 1.0 range
        speed = value / 100.0
        self.value_changed.emit(self.motor_id, speed)

    def _on_released(self) -> None:
        """Handle slider release."""
        if self._auto_zero:
            self._slider.setValue(0)
        self.released.emit(self.motor_id)

    def speed(self) -> float:
        """Get speed as float (-1.0 to 1.0)."""
        return self._slider.value() / 100.0
