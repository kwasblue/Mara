# mara_host/gui/panels/pinout/pin_info.py
"""Pin details info widget."""

from PySide6.QtWidgets import (
    QGroupBox,
    QFormLayout,
    QLabel,
)


class PinInfoWidget(QGroupBox):
    """Widget for displaying detailed pin information."""

    def __init__(self, parent=None):
        super().__init__("Pin Details", parent)
        self._pin_service = None
        self._setup_ui()

    def set_pin_service(self, pin_service) -> None:
        """Set the pin service instance."""
        self._pin_service = pin_service

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)

        self.gpio_label = QLabel("--")
        self.gpio_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addRow("GPIO:", self.gpio_label)

        self.name_label = QLabel("--")
        layout.addRow("Name:", self.name_label)

        self.caps_label = QLabel("--")
        self.caps_label.setWordWrap(True)
        layout.addRow("Capabilities:", self.caps_label)

        self.adc_label = QLabel("--")
        layout.addRow("ADC:", self.adc_label)

        self.touch_label = QLabel("--")
        layout.addRow("Touch:", self.touch_label)

        self.notes_label = QLabel("--")
        self.notes_label.setWordWrap(True)
        self.notes_label.setStyleSheet("color: #EAB308;")
        layout.addRow("Notes:", self.notes_label)

    def show_pin(self, gpio: int) -> None:
        """Show detailed info for a pin."""
        if not self._pin_service:
            return

        try:
            info = self._pin_service.get_pin_info(gpio)
            if not info:
                return

            self.gpio_label.setText(f"GPIO {gpio}")

            # Get assignment name
            assignments = self._pin_service.get_assignments()
            name = None
            for n, g in assignments.items():
                if g == gpio:
                    name = n
                    break
            self.name_label.setText(name or "(unassigned)")

            # Capabilities
            caps = self._pin_service.capability_string(gpio)
            self.caps_label.setText(caps)

            # ADC
            adc_channel = getattr(info, "adc_channel", None)
            self.adc_label.setText(adc_channel if adc_channel else "None")

            # Touch
            touch = getattr(info, "touch_channel", None)
            self.touch_label.setText(f"Touch {touch}" if touch is not None else "None")

            # Notes/warnings
            notes = getattr(info, "notes", "") or ""
            warning = getattr(info, "warning", "") or ""
            if self._pin_service.is_flash_pin(gpio):
                notes = "DO NOT USE - Flash connected"
            elif self._pin_service.is_boot_pin(gpio):
                notes = f"Boot pin - {warning}" if warning else "Boot strapping pin"
            elif warning:
                notes = warning
            self.notes_label.setText(notes or "None")

        except Exception:
            pass

    def clear(self) -> None:
        """Clear all displayed info."""
        self.gpio_label.setText("--")
        self.name_label.setText("--")
        self.caps_label.setText("--")
        self.adc_label.setText("--")
        self.touch_label.setText("--")
        self.notes_label.setText("--")
