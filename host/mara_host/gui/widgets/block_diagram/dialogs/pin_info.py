# mara_host/gui/widgets/block_diagram/dialogs/pin_info.py
"""Pin information popup dialog for block diagrams."""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QGridLayout,
    QGroupBox,
)
from PySide6.QtGui import QFont, QColor

from ..core.esp32_pinout import ESP32PinInfo, get_pin_info, PIN_CATEGORY_COLORS


class PinInfoDialog(QDialog):
    """
    Popup dialog showing detailed ESP32 pin information.

    Shows when user clicks on a GPIO pin in the block diagram.
    """

    pin_assigned = Signal(int, str)  # gpio, name

    def __init__(self, gpio: int, parent=None):
        super().__init__(parent)
        self.gpio = gpio
        self.pin_info = get_pin_info(gpio)

        self.setWindowTitle(f"GPIO {gpio} Info")
        self.setMinimumWidth(380)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main frame with border
        frame = QFrame()
        frame.setObjectName("pinInfoFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(16, 12, 16, 12)
        frame_layout.setSpacing(12)

        # Header with GPIO number and category color
        header = self._create_header()
        frame_layout.addWidget(header)

        if self.pin_info:
            # Capabilities section
            caps = self._create_capabilities()
            frame_layout.addWidget(caps)

            # Functions section
            funcs = self._create_functions()
            frame_layout.addWidget(funcs)

            # Warnings section (if any)
            if self.pin_info.warning or self.pin_info.flash_connected:
                warnings = self._create_warnings()
                frame_layout.addWidget(warnings)

            # Notes section
            if self.pin_info.notes:
                notes = self._create_notes()
                frame_layout.addWidget(notes)
        else:
            no_info = QLabel("No detailed information available for this GPIO.")
            no_info.setStyleSheet("color: #9CA3AF;")
            frame_layout.addWidget(no_info)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondary")
        close_btn.clicked.connect(self.close)
        frame_layout.addWidget(close_btn)

        layout.addWidget(frame)

    def _create_header(self) -> QWidget:
        """Create header with GPIO number and type indicator."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 8)

        # GPIO number with category color indicator
        gpio_label = QLabel(f"GPIO {self.gpio}")
        gpio_label.setFont(QFont("SF Pro Display", 18, QFont.Bold))
        gpio_label.setStyleSheet("color: #F9FAFB;")
        layout.addWidget(gpio_label)

        layout.addStretch()

        # Category badge
        if self.pin_info:
            category = self.pin_info.color_category
            color = PIN_CATEGORY_COLORS.get(category, "#6B7280")
            badge_text = category.upper().replace("_", " ")

            badge = QLabel(badge_text)
            badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    color: white;
                    padding: 4px 10px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }}
            """)
            layout.addWidget(badge)

        return widget

    def _create_capabilities(self) -> QGroupBox:
        """Create capabilities display."""
        group = QGroupBox("Capabilities")
        layout = QGridLayout(group)
        layout.setSpacing(8)

        row = 0
        col = 0

        # I/O capability
        if self.pin_info.input_only:
            self._add_cap_badge(layout, "INPUT ONLY", "#A855F7", row, col)
        elif self.pin_info.input and self.pin_info.output:
            self._add_cap_badge(layout, "I/O", "#10B981", row, col)
        col += 1

        # PWM
        if self.pin_info.output and not self.pin_info.input_only:
            self._add_cap_badge(layout, "PWM", "#F59E0B", row, col)
            col += 1

        # ADC
        if self.pin_info.adc1_channel is not None:
            self._add_cap_badge(layout, f"ADC1_{self.pin_info.adc1_channel}", "#EC4899", row, col)
            col += 1
        if self.pin_info.adc2_channel is not None:
            self._add_cap_badge(layout, f"ADC2_{self.pin_info.adc2_channel}", "#EC4899", row, col)
            col += 1

        # Wrap to next row
        if col >= 4:
            row += 1
            col = 0

        # DAC
        if self.pin_info.dac_channel is not None:
            self._add_cap_badge(layout, f"DAC_{self.pin_info.dac_channel}", "#8B5CF6", row, col)
            col += 1

        # Touch
        if self.pin_info.touch_channel is not None:
            self._add_cap_badge(layout, f"TOUCH_{self.pin_info.touch_channel}", "#14B8A6", row, col)
            col += 1

        # RTC
        if self.pin_info.rtc_gpio is not None:
            self._add_cap_badge(layout, f"RTC_GPIO{self.pin_info.rtc_gpio}", "#6366F1", row, col)
            col += 1

        return group

    def _add_cap_badge(self, layout: QGridLayout, text: str, color: str, row: int, col: int) -> None:
        """Add a capability badge to the grid."""
        badge = QLabel(text)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {color}33;
                color: {color};
                padding: 3px 8px;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
                border: 1px solid {color}66;
            }}
        """)
        badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(badge, row, col)

    def _create_functions(self) -> QGroupBox:
        """Create alternate functions display."""
        group = QGroupBox("Alternate Functions")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        functions = []

        # SPI
        if self.pin_info.hspi:
            functions.append(("HSPI", self.pin_info.hspi, "#3B82F6"))
        if self.pin_info.vspi:
            functions.append(("VSPI", self.pin_info.vspi, "#3B82F6"))

        # I2C
        if self.pin_info.i2c:
            functions.append(("I2C", self.pin_info.i2c, "#06B6D4"))

        # UART
        if self.pin_info.uart0:
            functions.append(("UART0", self.pin_info.uart0, "#22C55E"))
        if self.pin_info.uart2:
            functions.append(("UART2", self.pin_info.uart2, "#22C55E"))

        # SD Card
        if self.pin_info.sd_card:
            functions.append(("SD Card", self.pin_info.sd_card, "#F97316"))

        if functions:
            for bus, func, color in functions:
                row = QHBoxLayout()
                bus_label = QLabel(f"{bus}:")
                bus_label.setStyleSheet(f"color: {color}; font-weight: bold; min-width: 60px;")
                row.addWidget(bus_label)

                func_label = QLabel(func)
                func_label.setStyleSheet("color: #E5E7EB;")
                row.addWidget(func_label)
                row.addStretch()

                layout.addLayout(row)
        else:
            none_label = QLabel("No alternate functions")
            none_label.setStyleSheet("color: #6B7280; font-style: italic;")
            layout.addWidget(none_label)

        return group

    def _create_warnings(self) -> QWidget:
        """Create warnings section."""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #7F1D1D;
                border: 1px solid #EF4444;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)

        header = QLabel("Warning")
        header.setStyleSheet("color: #FCA5A5; font-weight: bold; font-size: 12px;")
        layout.addWidget(header)

        if self.pin_info.flash_connected:
            text = "DO NOT USE - Connected to internal flash memory!"
        else:
            text = self.pin_info.warning

        warning_label = QLabel(text)
        warning_label.setStyleSheet("color: #FECACA;")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)

        return widget

    def _create_notes(self) -> QWidget:
        """Create notes section."""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #1E3A5F;
                border: 1px solid #3B82F6;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)

        header = QLabel("Notes")
        header.setStyleSheet("color: #93C5FD; font-weight: bold; font-size: 12px;")
        layout.addWidget(header)

        notes_label = QLabel(self.pin_info.notes)
        notes_label.setStyleSheet("color: #BFDBFE;")
        notes_label.setWordWrap(True)
        layout.addWidget(notes_label)

        return widget

    def _apply_style(self) -> None:
        """Apply dialog styling."""
        self.setStyleSheet("""
            QDialog {
                background-color: #18181B;
            }
            QFrame#pinInfoFrame {
                background-color: #18181B;
                border: 1px solid #3F3F46;
                border-radius: 8px;
            }
            QGroupBox {
                font-weight: bold;
                color: #A1A1AA;
                border: 1px solid #27272A;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #3F3F46;
                color: #F9FAFB;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #52525B;
            }
        """)


def show_pin_info_popup(gpio: int, parent=None, pos=None) -> None:
    """Show pin info popup at the given position."""
    dialog = PinInfoDialog(gpio, parent)
    if pos:
        dialog.move(pos)
    dialog.exec()
