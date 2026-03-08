# mara_host/gui/widgets/controls/spinbox_row.py
"""
Single labeled spinbox widget.

A simple row with label + spinbox for single value editing.
"""


from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QDoubleSpinBox,
    QSpinBox,
)
from PySide6.QtCore import Signal


class SpinBoxRow(QWidget):
    """
    Single labeled spinbox in a horizontal layout.

    Emits:
        value_changed: (value: float) when value changes

    Example:
        row = SpinBoxRow("Speed:", 0, 100, 50, suffix=" m/s")
        row.value_changed.connect(lambda v: print(f"Speed: {v}"))
    """

    value_changed = Signal(float)

    def __init__(
        self,
        label: str,
        min_value: float = 0.0,
        max_value: float = 100.0,
        default: float = 0.0,
        step: float = 1.0,
        decimals: int = 2,
        suffix: str = "",
        is_int: bool = False,
        stretch_after: bool = True,
        parent=None,
    ):
        """
        Initialize spinbox row.

        Args:
            label: Label text
            min_value: Minimum value
            max_value: Maximum value
            default: Default value
            step: Step increment
            decimals: Decimal places (ignored for int)
            suffix: Suffix string
            is_int: Use integer spinbox
            stretch_after: Add stretch after spinbox
            parent: Parent widget
        """
        super().__init__(parent)

        self._is_int = is_int
        self._setup_ui(
            label, min_value, max_value, default, step, decimals, suffix, stretch_after
        )

    def _setup_ui(
        self,
        label: str,
        min_value: float,
        max_value: float,
        default: float,
        step: float,
        decimals: int,
        suffix: str,
        stretch_after: bool,
    ) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label
        self._label = QLabel(label)
        layout.addWidget(self._label)

        # Spinbox
        if self._is_int:
            self._spinbox = QSpinBox()
            self._spinbox.setRange(int(min_value), int(max_value))
            self._spinbox.setValue(int(default))
            self._spinbox.setSingleStep(int(step) or 1)
        else:
            self._spinbox = QDoubleSpinBox()
            self._spinbox.setRange(min_value, max_value)
            self._spinbox.setValue(default)
            self._spinbox.setSingleStep(step)
            self._spinbox.setDecimals(decimals)

        if suffix:
            self._spinbox.setSuffix(suffix)

        self._spinbox.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self._spinbox)

        if stretch_after:
            layout.addStretch()

    def _on_value_changed(self, value: float) -> None:
        """Handle value change."""
        self.value_changed.emit(float(value))

    def value(self) -> float:
        """Get current value."""
        return float(self._spinbox.value())

    def setValue(self, value: float) -> None:
        """Set value."""
        if self._is_int:
            self._spinbox.setValue(int(value))
        else:
            self._spinbox.setValue(value)

    def setRange(self, min_value: float, max_value: float) -> None:
        """Set value range."""
        if self._is_int:
            self._spinbox.setRange(int(min_value), int(max_value))
        else:
            self._spinbox.setRange(min_value, max_value)

    def setEnabled(self, enabled: bool) -> None:
        """Enable/disable the spinbox."""
        self._spinbox.setEnabled(enabled)
        super().setEnabled(enabled)
