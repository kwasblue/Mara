# mara_host/gui/widgets/displays/label_display.py
"""
Styled label display widget.

Provides a styled numeric value display with optional label and unit.
"""


from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
)
from PySide6.QtCore import Qt


class LabelDisplay(QWidget):
    """
    Styled numeric value display.

    Displays a value with optional label and unit in a consistent style.

    Example:
        display = LabelDisplay("Speed", "m/s", min_width=60)
        display.setValue(3.14)
        display.setText("N/A")
    """

    def __init__(
        self,
        label: str = "",
        unit: str = "",
        initial_value: str = "--",
        min_width: int = 50,
        font_size: int = 13,
        monospace: bool = True,
        alignment: Qt.AlignmentFlag = Qt.AlignRight,
        parent=None,
    ):
        """
        Initialize label display.

        Args:
            label: Label text (shown before value)
            unit: Unit text (shown after value)
            initial_value: Initial display text
            min_width: Minimum width for value label
            font_size: Font size in pixels
            monospace: Use monospace font
            alignment: Value text alignment
            parent: Parent widget
        """
        super().__init__(parent)

        self._format = "{:.2f}"
        self._setup_ui(
            label, unit, initial_value, min_width, font_size, monospace, alignment
        )

    def _setup_ui(
        self,
        label: str,
        unit: str,
        initial_value: str,
        min_width: int,
        font_size: int,
        monospace: bool,
        alignment: Qt.AlignmentFlag,
    ) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label (optional)
        if label:
            self._label = QLabel(label)
            self._label.setStyleSheet("color: #52525B; font-size: 11px;")
            layout.addWidget(self._label)
        else:
            self._label = None

        # Value
        font_family = "'Menlo', 'JetBrains Mono', monospace" if monospace else "inherit"
        self._value_label = QLabel(initial_value)
        self._value_label.setMinimumWidth(min_width)
        self._value_label.setAlignment(alignment | Qt.AlignVCenter)
        self._value_label.setStyleSheet(
            f"font-family: {font_family}; "
            f"color: #FAFAFA; "
            f"font-size: {font_size}px;"
        )
        layout.addWidget(self._value_label)

        # Unit (optional)
        if unit:
            self._unit_label = QLabel(unit)
            self._unit_label.setStyleSheet("color: #52525B; font-size: 11px;")
            layout.addWidget(self._unit_label)
        else:
            self._unit_label = None

    def setValue(self, value: float) -> None:
        """
        Set numeric value.

        Args:
            value: Numeric value to display
        """
        self._value_label.setText(self._format.format(value))

    def setText(self, text: str) -> None:
        """
        Set raw text value.

        Args:
            text: Text to display
        """
        self._value_label.setText(text)

    def setFormat(self, fmt: str) -> None:
        """
        Set format string for numeric values.

        Args:
            fmt: Python format string (e.g., "{:.3f}")
        """
        self._format = fmt

    def text(self) -> str:
        """Get current display text."""
        return self._value_label.text()

    def setColor(self, color: str) -> None:
        """
        Set value text color.

        Args:
            color: CSS color string
        """
        style = self._value_label.styleSheet()
        # Replace color in existing style
        import re
        style = re.sub(r'color:\s*[^;]+;', f'color: {color};', style)
        self._value_label.setStyleSheet(style)

    def setLabel(self, label: str) -> None:
        """Set label text."""
        if self._label:
            self._label.setText(label)

    def setUnit(self, unit: str) -> None:
        """Set unit text."""
        if self._unit_label:
            self._unit_label.setText(unit)
