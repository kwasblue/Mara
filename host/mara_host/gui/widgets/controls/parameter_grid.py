# mara_host/gui/widgets/controls/parameter_grid.py
"""
Parameter grid widget.

Provides a grid of labeled spinboxes for parameter editing
(e.g., PID gains, configuration values).
"""

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QLabel,
    QDoubleSpinBox,
    QSpinBox,
)
from PySide6.QtCore import Signal


@dataclass
class ParameterSpec:
    """Specification for a parameter in the grid."""
    key: str
    label: str
    min_value: float = 0.0
    max_value: float = 100.0
    default: float = 0.0
    step: float = 0.1
    decimals: int = 3
    suffix: str = ""
    is_int: bool = False


class ParameterGrid(QWidget):
    """
    Grid of labeled parameter spinboxes.

    Emits:
        value_changed: (key: str, value: float) when any parameter changes
        values_changed: (dict) when any parameter changes (all values)

    Example:
        params = [
            ParameterSpec("kp", "Kp", 0, 100, 1.0, 0.1, 3),
            ParameterSpec("ki", "Ki", 0, 100, 0.0, 0.01, 3),
            ParameterSpec("kd", "Kd", 0, 100, 0.0, 0.01, 3),
        ]
        grid = ParameterGrid(params, columns=2)
        grid.value_changed.connect(lambda k, v: print(f"{k} = {v}"))
    """

    value_changed = Signal(str, float)  # key, value
    values_changed = Signal(dict)  # all values

    def __init__(
        self,
        parameters: list[ParameterSpec],
        columns: int = 2,
        parent=None,
    ):
        """
        Initialize parameter grid.

        Args:
            parameters: List of ParameterSpec definitions
            columns: Number of columns (label+spinbox pairs)
            parent: Parent widget
        """
        super().__init__(parent)

        self._parameters = parameters
        self._columns = columns
        self._spinboxes: dict[str, QDoubleSpinBox | QSpinBox] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setSpacing(8)

        row = 0
        col = 0

        for param in self._parameters:
            # Label
            label = QLabel(f"{param.label}:")
            layout.addWidget(label, row, col * 2)

            # Spinbox
            if param.is_int:
                spinbox = QSpinBox()
                spinbox.setRange(int(param.min_value), int(param.max_value))
                spinbox.setValue(int(param.default))
                spinbox.setSingleStep(int(param.step) or 1)
            else:
                spinbox = QDoubleSpinBox()
                spinbox.setRange(param.min_value, param.max_value)
                spinbox.setValue(param.default)
                spinbox.setSingleStep(param.step)
                spinbox.setDecimals(param.decimals)

            if param.suffix:
                spinbox.setSuffix(param.suffix)

            spinbox.valueChanged.connect(
                lambda v, k=param.key: self._on_value_changed(k, v)
            )

            self._spinboxes[param.key] = spinbox
            layout.addWidget(spinbox, row, col * 2 + 1)

            col += 1
            if col >= self._columns:
                col = 0
                row += 1

    def _on_value_changed(self, key: str, value: float) -> None:
        """Handle parameter value change."""
        self.value_changed.emit(key, value)
        self.values_changed.emit(self.values())

    def value(self, key: str) -> float:
        """Get a parameter value by key."""
        if key in self._spinboxes:
            return self._spinboxes[key].value()
        return 0.0

    def setValue(self, key: str, value: float) -> None:
        """Set a parameter value by key."""
        if key in self._spinboxes:
            self._spinboxes[key].setValue(value)

    def values(self) -> dict[str, float]:
        """Get all parameter values."""
        return {key: spinbox.value() for key, spinbox in self._spinboxes.items()}

    def setValues(self, values: dict[str, float]) -> None:
        """Set multiple parameter values."""
        for key, value in values.items():
            if key in self._spinboxes:
                self._spinboxes[key].setValue(value)

    def setEnabled(self, enabled: bool) -> None:
        """Enable/disable all spinboxes."""
        for spinbox in self._spinboxes.values():
            spinbox.setEnabled(enabled)
        super().setEnabled(enabled)
