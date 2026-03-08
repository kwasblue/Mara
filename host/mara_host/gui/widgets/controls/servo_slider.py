# mara_host/gui/widgets/controls/servo_slider.py
"""
Servo slider widget.

Provides a slider for controlling servo angle with labels and units.
"""

from PySide6.QtCore import Signal

from .slider_base import RangeSliderWidget


class ServoSliderGroup(RangeSliderWidget):
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
        super().__init__(
            item_id=servo_id,
            label=label or f"S{servo_id}",
            unit="deg",
            min_value=min_angle,
            max_value=max_angle,
            initial_value=initial_angle,
            parent=parent,
        )

    @property
    def servo_id(self) -> int:
        """Get servo ID."""
        return self._item_id

    def _on_value_changed(self, value: int) -> None:
        """Handle slider value change."""
        self.value_changed.emit(self.servo_id, float(value))

    def _on_released(self) -> None:
        """Handle slider release."""
        self.released.emit(self.servo_id, float(self._slider.value()))

    def angle(self) -> float:
        """Get angle as float."""
        return float(self._slider.value())

    def center(self) -> None:
        """Move to center position."""
        center = (self._min + self._max) // 2
        self.setValue(center)
