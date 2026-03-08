# mara_host/gui/panels/pinout/pin_wizard.py
"""Pin quick setup wizard widget."""

from typing import Dict

from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QTextEdit,
)
from PySide6.QtCore import Signal


WIZARD_MAP = {
    "DC Motor": "motor",
    "Encoder": "encoder",
    "Stepper": "stepper",
    "Servo": "servo",
    "I2C": "i2c",
    "SPI": "spi",
    "UART": "uart",
}


class PinWizardWidget(QGroupBox):
    """
    Widget for quick pin setup wizards.

    Signals:
        pins_suggested(dict): Emitted when pins are suggested {name: gpio}
        pins_applied(dict): Emitted when suggestion is applied {name: gpio}
    """

    pins_suggested = Signal(dict)
    pins_applied = Signal(dict)

    def __init__(self, parent=None):
        super().__init__("Quick Setup", parent)
        self._pin_service = None
        self._current_suggestion: Dict[str, int] = {}
        self._setup_ui()

    def set_pin_service(self, pin_service) -> None:
        """Set the pin service instance."""
        self._pin_service = pin_service

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Wizard selector
        wizard_layout = QHBoxLayout()

        self.wizard_combo = QComboBox()
        self.wizard_combo.addItems(list(WIZARD_MAP.keys()))
        wizard_layout.addWidget(self.wizard_combo, 1)

        # Instance number
        wizard_layout.addWidget(QLabel("#"))
        self.instance_input = QLineEdit("0")
        self.instance_input.setMaximumWidth(40)
        wizard_layout.addWidget(self.instance_input)

        layout.addLayout(wizard_layout)

        # Suggest button
        suggest_btn = QPushButton("Suggest Pins")
        suggest_btn.clicked.connect(self._suggest_pins)
        layout.addWidget(suggest_btn)

        # Apply button
        self.apply_btn = QPushButton("Apply Suggestion")
        self.apply_btn.setObjectName("success")
        self.apply_btn.clicked.connect(self._apply_suggestion)
        self.apply_btn.setEnabled(False)
        layout.addWidget(self.apply_btn)

        # Suggestion display
        self.suggestion_text = QTextEdit()
        self.suggestion_text.setReadOnly(True)
        self.suggestion_text.setMaximumHeight(100)
        self.suggestion_text.setStyleSheet(
            "font-family: monospace; background-color: #1E1E2E;"
        )
        layout.addWidget(self.suggestion_text)

    def _suggest_pins(self) -> None:
        """Suggest pins for the selected use case."""
        if not self._pin_service:
            return

        wizard = self.wizard_combo.currentText()
        use_case = WIZARD_MAP.get(wizard, "motor")
        instance = self.instance_input.text() or "0"

        try:
            # Get recommendation
            method_name = f"recommend_{use_case}_pins"
            if hasattr(self._pin_service, method_name):
                needs_id = {"motor", "encoder", "stepper", "servo", "uart"}
                if use_case in needs_id:
                    recommendations = getattr(self._pin_service, method_name)(instance)
                else:
                    recommendations = getattr(self._pin_service, method_name)()
            else:
                recommendations = self._pin_service.suggest_pins(use_case)

            if not recommendations:
                self.suggestion_text.setPlainText("No suitable pins found")
                self.apply_btn.setEnabled(False)
                return

            # Format suggestions
            text = f"{wizard} #{instance}:\n"
            self._current_suggestion = {}

            # Handle GroupRecommendation (dataclass with suggested_assignments)
            if hasattr(recommendations, 'suggested_assignments'):
                for name, gpio in recommendations.suggested_assignments.items():
                    text += f"  {name}: GPIO {gpio}\n"
                    self._current_suggestion[name] = gpio
                if recommendations.warnings:
                    text += "\nWarnings:\n"
                    for warning in recommendations.warnings:
                        text += f"  - {warning}\n"
            elif isinstance(recommendations, dict):
                for name, gpio in recommendations.items():
                    text += f"  {name}: GPIO {gpio}\n"
                    self._current_suggestion[name] = gpio
            elif isinstance(recommendations, list):
                for i, rec in enumerate(recommendations[:4]):
                    name = f"{use_case.upper()}_{instance}_{i}"
                    text += f"  {name}: GPIO {rec.gpio} (score: {rec.score})\n"
                    self._current_suggestion[name] = rec.gpio
            else:
                self.suggestion_text.setPlainText(f"Unexpected type: {type(recommendations)}")
                return

            self.suggestion_text.setPlainText(text)
            self.apply_btn.setEnabled(bool(self._current_suggestion))
            self.pins_suggested.emit(self._current_suggestion)

        except Exception as e:
            self.suggestion_text.setPlainText(f"Error: {e}")
            self.apply_btn.setEnabled(False)

    def _apply_suggestion(self) -> None:
        """Apply the current suggestion."""
        if not self._pin_service or not self._current_suggestion:
            return

        try:
            for name, gpio in self._current_suggestion.items():
                self._pin_service.assign(name, gpio)

            self.pins_applied.emit(self._current_suggestion.copy())
            self._current_suggestion = {}
            self.suggestion_text.clear()
            self.apply_btn.setEnabled(False)

        except Exception as e:
            self.suggestion_text.setPlainText(f"Failed to apply: {e}")

    def get_current_suggestion(self) -> Dict[str, int]:
        """Get the current suggestion."""
        return self._current_suggestion.copy()
