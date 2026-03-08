# mara_host/gui/widgets/controls/slider_base.py
"""
Base class for range slider widgets.

Provides common functionality for sliders with labels and value displays.
"""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QSlider,
)
from PySide6.QtCore import Qt, Signal


class RangeSliderWidget(QWidget):
    """
    Base class for range sliders with label and value display.

    Provides common layout and styling for sliders. Subclasses
    implement value conversion and signal emission.

    Layout: [Label] [----Slider----] [Value] [Unit]

    Subclasses should:
    - Define value_changed and released signals with appropriate signatures
    - Override _on_value_changed() to emit value_changed with converted value
    - Override _on_released() to handle release behavior
    """

    def __init__(
        self,
        item_id: int,
        label: str,
        unit: str,
        min_value: int,
        max_value: int,
        initial_value: int,
        parent=None,
    ):
        """
        Initialize slider widget.

        Args:
            item_id: Identifier for the controlled item
            label: Label text
            unit: Unit text (e.g., "%", "deg")
            min_value: Minimum slider value
            max_value: Maximum slider value
            initial_value: Initial slider position
            parent: Parent widget
        """
        super().__init__(parent)

        self._item_id = item_id
        self._min = min_value
        self._max = max_value
        self._unit = unit

        self._setup_ui(label, initial_value)

    @property
    def item_id(self) -> int:
        """Get the item identifier."""
        return self._item_id

    def _setup_ui(self, label: str, initial_value: int) -> None:
        """Set up the widget UI."""
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
        self._slider.valueChanged.connect(self._handle_value_changed)
        self._slider.sliderReleased.connect(self._handle_released)
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
        unit_label = QLabel(self._unit)
        unit_label.setStyleSheet("color: #52525B; font-size: 11px;")
        layout.addWidget(unit_label)

    def _handle_value_changed(self, value: int) -> None:
        """Internal handler for value changes."""
        self._value_label.setText(str(value))
        self._on_value_changed(value)

    def _handle_released(self) -> None:
        """Internal handler for slider release."""
        self._on_released()

    def _on_value_changed(self, value: int) -> None:
        """
        Handle slider value change - override in subclass.

        Args:
            value: New slider value
        """
        pass

    def _on_released(self) -> None:
        """Handle slider release - override in subclass."""
        pass

    def value(self) -> int:
        """Get current slider value."""
        return self._slider.value()

    def setValue(self, value: int) -> None:
        """Set slider value."""
        self._slider.setValue(value)

    def setRange(self, min_value: int, max_value: int) -> None:
        """Set slider range."""
        self._min = min_value
        self._max = max_value
        self._slider.setRange(min_value, max_value)

    def setEnabled(self, enabled: bool) -> None:
        """Enable/disable the slider."""
        self._slider.setEnabled(enabled)
        super().setEnabled(enabled)
