# mara_host/gui/panels/pinout/pin_info.py
"""Pin details info widget using comprehensive ESP32 pinout data."""

from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QFrame,
    QGridLayout,
)
from PySide6.QtCore import Qt

# Import ESP32 pinout data
from mara_host.gui.widgets.block_diagram.core.esp32_pinout import (
    get_pin_info as get_esp32_pin_info,
    PIN_CATEGORY_COLORS,
)


class PinInfoWidget(QGroupBox):
    """Widget for displaying detailed ESP32 pin information."""

    def __init__(self, parent=None):
        super().__init__("Pin Details", parent)
        self._pin_service = None
        self._setup_ui()

    def set_pin_service(self, pin_service) -> None:
        """Set the pin service instance."""
        self._pin_service = pin_service

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header with GPIO number and category
        header_layout = QHBoxLayout()
        self.gpio_label = QLabel("--")
        self.gpio_label.setStyleSheet("font-weight: bold; font-size: 18px; color: #F9FAFB;")
        header_layout.addWidget(self.gpio_label)
        header_layout.addStretch()

        self.category_badge = QLabel("")
        header_layout.addWidget(self.category_badge)
        layout.addLayout(header_layout)

        # Assignment name
        self.name_label = QLabel("(unassigned)")
        self.name_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        layout.addWidget(self.name_label)

        # Capabilities grid
        self.caps_frame = QFrame()
        self.caps_frame.setStyleSheet("""
            QFrame {
                background-color: #1F1F23;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self.caps_layout = QGridLayout(self.caps_frame)
        self.caps_layout.setSpacing(6)
        layout.addWidget(self.caps_frame)

        # Functions section
        form = QFormLayout()
        form.setSpacing(6)

        self.io_label = QLabel("--")
        form.addRow("I/O:", self.io_label)

        self.adc_label = QLabel("--")
        form.addRow("ADC:", self.adc_label)

        self.dac_label = QLabel("--")
        form.addRow("DAC:", self.dac_label)

        self.touch_label = QLabel("--")
        form.addRow("Touch:", self.touch_label)

        self.spi_label = QLabel("--")
        form.addRow("SPI:", self.spi_label)

        self.i2c_label = QLabel("--")
        form.addRow("I2C:", self.i2c_label)

        self.uart_label = QLabel("--")
        form.addRow("UART:", self.uart_label)

        layout.addLayout(form)

        # Notes/warnings
        self.notes_frame = QFrame()
        self.notes_frame.setVisible(False)
        notes_layout = QVBoxLayout(self.notes_frame)
        notes_layout.setContentsMargins(8, 8, 8, 8)
        self.notes_label = QLabel("")
        self.notes_label.setWordWrap(True)
        notes_layout.addWidget(self.notes_label)
        layout.addWidget(self.notes_frame)

        layout.addStretch()

    def _add_cap_badge(self, text: str, color: str, row: int, col: int) -> None:
        """Add a capability badge."""
        badge = QLabel(text)
        badge.setAlignment(Qt.AlignCenter)
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
        self.caps_layout.addWidget(badge, row, col)

    def _clear_caps_layout(self) -> None:
        """Clear the capabilities layout."""
        while self.caps_layout.count():
            item = self.caps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_pin(self, gpio: int) -> None:
        """Show detailed info for a pin."""
        # Get ESP32 pinout info
        esp_info = get_esp32_pin_info(gpio)

        self.gpio_label.setText(f"GPIO {gpio}")

        # Get assignment name from service if available
        name = None
        if self._pin_service:
            try:
                assignments = self._pin_service.get_assignments()
                for n, g in assignments.items():
                    if g == gpio:
                        name = n
                        break
            except Exception:
                pass

        if name:
            self.name_label.setText(f"Assigned: {name}")
            self.name_label.setStyleSheet("color: #22C55E; font-size: 12px; font-weight: bold;")
        else:
            self.name_label.setText("(unassigned)")
            self.name_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")

        if not esp_info:
            self._show_basic_info(gpio)
            return

        # Category badge
        category = esp_info.color_category
        color = PIN_CATEGORY_COLORS.get(category, "#6B7280")
        badge_text = category.upper().replace("_", " ")
        self.category_badge.setText(badge_text)
        self.category_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        self.category_badge.setVisible(True)

        # Clear and populate capabilities
        self._clear_caps_layout()
        row, col = 0, 0

        if esp_info.input_only:
            self._add_cap_badge("INPUT ONLY", "#A855F7", row, col)
            col += 1
        elif esp_info.input and esp_info.output:
            self._add_cap_badge("I/O", "#10B981", row, col)
            col += 1

        if esp_info.output and not esp_info.input_only:
            self._add_cap_badge("PWM", "#F59E0B", row, col)
            col += 1

        if col >= 3:
            row += 1
            col = 0

        if esp_info.adc1_channel is not None:
            self._add_cap_badge(f"ADC1_{esp_info.adc1_channel}", "#EC4899", row, col)
            col += 1
        if esp_info.adc2_channel is not None:
            self._add_cap_badge(f"ADC2_{esp_info.adc2_channel}", "#EC4899", row, col)
            col += 1

        if col >= 3:
            row += 1
            col = 0

        if esp_info.dac_channel is not None:
            self._add_cap_badge(f"DAC_{esp_info.dac_channel}", "#8B5CF6", row, col)
            col += 1
        if esp_info.touch_channel is not None:
            self._add_cap_badge(f"TOUCH_{esp_info.touch_channel}", "#14B8A6", row, col)
            col += 1

        # I/O
        if esp_info.input_only:
            self.io_label.setText("Input only (no pullup/pulldown)")
            self.io_label.setStyleSheet("color: #A855F7;")
        elif esp_info.input and esp_info.output:
            self.io_label.setText("Input / Output")
            self.io_label.setStyleSheet("color: #10B981;")
        else:
            self.io_label.setText("--")
            self.io_label.setStyleSheet("")

        # ADC
        adc_parts = []
        if esp_info.adc1_channel is not None:
            adc_parts.append(f"ADC1 Ch{esp_info.adc1_channel}")
        if esp_info.adc2_channel is not None:
            adc_parts.append(f"ADC2 Ch{esp_info.adc2_channel}")
        if adc_parts:
            adc_text = ", ".join(adc_parts)
            if esp_info.adc2_channel is not None:
                adc_text += " (ADC2 not available with WiFi)"
            self.adc_label.setText(adc_text)
        else:
            self.adc_label.setText("None")

        # DAC
        if esp_info.dac_channel is not None:
            self.dac_label.setText(f"DAC Channel {esp_info.dac_channel}")
        else:
            self.dac_label.setText("None")

        # Touch
        if esp_info.touch_channel is not None:
            self.touch_label.setText(f"Touch Sensor {esp_info.touch_channel}")
        else:
            self.touch_label.setText("None")

        # SPI
        spi_parts = []
        if esp_info.hspi:
            spi_parts.append(f"HSPI {esp_info.hspi}")
        if esp_info.vspi:
            spi_parts.append(f"VSPI {esp_info.vspi}")
        self.spi_label.setText(", ".join(spi_parts) if spi_parts else "None")

        # I2C
        if esp_info.i2c:
            self.i2c_label.setText(f"I2C {esp_info.i2c} (default)")
        else:
            self.i2c_label.setText("None")

        # UART
        uart_parts = []
        if esp_info.uart0:
            uart_parts.append(f"UART0 {esp_info.uart0}")
        if esp_info.uart2:
            uart_parts.append(f"UART2 {esp_info.uart2}")
        self.uart_label.setText(", ".join(uart_parts) if uart_parts else "None")

        # Notes/warnings
        if esp_info.flash_connected:
            self.notes_frame.setVisible(True)
            self.notes_frame.setStyleSheet("""
                QFrame {
                    background-color: #7F1D1D;
                    border: 1px solid #EF4444;
                    border-radius: 6px;
                }
            """)
            self.notes_label.setText("DO NOT USE - Connected to internal flash!")
            self.notes_label.setStyleSheet("color: #FECACA; font-weight: bold;")
        elif esp_info.warning:
            self.notes_frame.setVisible(True)
            self.notes_frame.setStyleSheet("""
                QFrame {
                    background-color: #78350F;
                    border: 1px solid #F59E0B;
                    border-radius: 6px;
                }
            """)
            self.notes_label.setText(esp_info.warning)
            self.notes_label.setStyleSheet("color: #FDE68A;")
        elif esp_info.notes:
            self.notes_frame.setVisible(True)
            self.notes_frame.setStyleSheet("""
                QFrame {
                    background-color: #1E3A5F;
                    border: 1px solid #3B82F6;
                    border-radius: 6px;
                }
            """)
            self.notes_label.setText(esp_info.notes)
            self.notes_label.setStyleSheet("color: #BFDBFE;")
        else:
            self.notes_frame.setVisible(False)

    def _show_basic_info(self, gpio: int) -> None:
        """Show basic info when ESP32 pinout data is not available."""
        self.category_badge.setVisible(False)
        self._clear_caps_layout()
        self.io_label.setText("--")
        self.io_label.setStyleSheet("")
        self.adc_label.setText("--")
        self.dac_label.setText("--")
        self.touch_label.setText("--")
        self.spi_label.setText("--")
        self.i2c_label.setText("--")
        self.uart_label.setText("--")
        self.notes_frame.setVisible(False)

        # Try to get info from pin service
        if self._pin_service:
            try:
                caps = self._pin_service.capability_string(gpio)
                self._add_cap_badge(caps, "#6B7280", 0, 0)
            except Exception:
                pass

    def clear(self) -> None:
        """Clear all displayed info."""
        self.gpio_label.setText("--")
        self.name_label.setText("(unassigned)")
        self.name_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        self.category_badge.setVisible(False)
        self._clear_caps_layout()
        self.io_label.setText("--")
        self.io_label.setStyleSheet("")
        self.adc_label.setText("--")
        self.dac_label.setText("--")
        self.touch_label.setText("--")
        self.spi_label.setText("--")
        self.i2c_label.setText("--")
        self.uart_label.setText("--")
        self.notes_frame.setVisible(False)
