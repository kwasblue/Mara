# mara_host/gui/widgets/displays/telemetry_grid.py
"""
Telemetry grid widget.

Provides a grid of label+value pairs for displaying telemetry data.
"""

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QLabel,
)


@dataclass
class TelemetrySpec:
    """Specification for a telemetry value in the grid."""
    key: str
    label: str
    unit: str = ""
    format: str = "{:.2f}"
    initial: str = "--"


class TelemetryGrid(QWidget):
    """
    Grid of telemetry label+value pairs.

    Displays multiple telemetry values in a compact grid layout.

    Example:
        specs = [
            TelemetrySpec("vx", "vx", "m/s"),
            TelemetrySpec("omega", "omega", "rad/s"),
            TelemetrySpec("count", "Count", "", "{:.0f}"),
        ]
        grid = TelemetryGrid(specs, columns=2)
        grid.update("vx", 1.5)
        grid.update("omega", 0.3)
    """

    def __init__(
        self,
        specs: list[TelemetrySpec],
        columns: int = 2,
        parent=None,
    ):
        """
        Initialize telemetry grid.

        Args:
            specs: List of TelemetrySpec definitions
            columns: Number of columns (label+value pairs per row)
            parent: Parent widget
        """
        super().__init__(parent)

        self._specs = {s.key: s for s in specs}
        self._columns = columns
        self._value_labels: dict[str, QLabel] = {}

        self._setup_ui(specs)

    def _setup_ui(self, specs: list[TelemetrySpec]) -> None:
        layout = QGridLayout(self)
        layout.setSpacing(8)

        row = 0
        col = 0

        for spec in specs:
            # Label
            label = QLabel(f"{spec.label}:")
            label.setStyleSheet("color: #71717A; font-size: 12px;")
            layout.addWidget(label, row, col * 3)

            # Value
            value_label = QLabel(spec.initial)
            value_label.setStyleSheet(
                "font-family: 'Menlo', 'JetBrains Mono', monospace; "
                "color: #FAFAFA; "
                "font-size: 13px;"
            )
            value_label.setMinimumWidth(50)
            self._value_labels[spec.key] = value_label
            layout.addWidget(value_label, row, col * 3 + 1)

            # Unit
            if spec.unit:
                unit_label = QLabel(spec.unit)
                unit_label.setStyleSheet("color: #52525B; font-size: 11px;")
                layout.addWidget(unit_label, row, col * 3 + 2)

            col += 1
            if col >= self._columns:
                col = 0
                row += 1

    def update(self, key: str, value: float) -> None:
        """
        Update a telemetry value.

        Args:
            key: Telemetry key
            value: New value
        """
        if key in self._value_labels and key in self._specs:
            spec = self._specs[key]
            self._value_labels[key].setText(spec.format.format(value))

    def setText(self, key: str, text: str) -> None:
        """
        Set raw text for a telemetry value.

        Args:
            key: Telemetry key
            text: Text to display
        """
        if key in self._value_labels:
            self._value_labels[key].setText(text)

    def reset(self) -> None:
        """Reset all values to initial state."""
        for key, spec in self._specs.items():
            if key in self._value_labels:
                self._value_labels[key].setText(spec.initial)

    def values(self) -> dict[str, str]:
        """Get all current display values."""
        return {key: label.text() for key, label in self._value_labels.items()}
