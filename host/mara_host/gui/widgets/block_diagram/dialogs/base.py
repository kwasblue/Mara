# mara_host/gui/widgets/block_diagram/dialogs/base.py
"""Base configuration dialog for block diagram elements."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QWidget,
    QLabel,
)


@dataclass
class FieldDef:
    """
    Definition for a config dialog field.

    Attributes:
        name: Field identifier (used as dict key)
        label: Display label for the field
        field_type: Widget type - "float", "int", "bool", "str", "choice"
        default: Default value when not in properties
        min_val: Minimum value for numeric types
        max_val: Maximum value for numeric types
        step: Step value for spinboxes
        decimals: Decimal places for float fields
        choices: List of choices for "choice" type
        group: Optional group name for organizing fields
        suffix: Optional suffix for spinboxes (e.g., "ms", "Hz")
        tooltip: Optional tooltip text
        live_update: Whether this field supports live updates
    """

    name: str
    label: str
    field_type: str = "float"
    default: Any = 0.0
    min_val: float = -1e9
    max_val: float = 1e9
    step: float = 0.1
    decimals: int = 3
    choices: Optional[list[str]] = None
    group: Optional[str] = None
    suffix: Optional[str] = None
    tooltip: Optional[str] = None
    live_update: bool = True


class BaseBlockConfigDialog(QDialog):
    """
    Base class for block configuration dialogs.

    Provides common functionality for creating configuration dialogs:
    - Automatic form layout generation from field definitions
    - Live tune checkbox with status indicator
    - OK/Cancel buttons
    - Value collection to dict

    Subclasses define fields as class attributes:

        class MotorConfigDialog(BaseBlockConfigDialog):
            dialog_title = "Motor Configuration"
            fields = [
                FieldDef("speed", "Speed", default=0.0, min_val=-1.0, max_val=1.0),
                FieldDef("acceleration", "Acceleration", default=1.0, min_val=0.0),
                FieldDef("enabled", "Enabled", field_type="bool", default=True),
            ]

    Signals:
        live_update(int, dict): Emitted when Live Tune is enabled and a
                                parameter changes. Args: (slot, {param: value})
    """

    dialog_title: str = "Configure Block"
    fields: list[FieldDef] = []
    show_live_tune: bool = True
    min_width: int = 350

    live_update = Signal(int, dict)

    def __init__(
        self,
        properties: dict,
        parent: Optional[QWidget] = None,
        controller: Any = None,
        slot: int = 0,
    ):
        """
        Initialize config dialog.

        Args:
            properties: Current block properties
            parent: Parent widget
            controller: RobotController for live tuning (optional)
            slot: Controller slot number for live updates
        """
        super().__init__(parent)
        self._properties = properties.copy()
        self._controller = controller
        self._slot = slot
        self._live_tune = False
        self._widgets: dict[str, QWidget] = {}

        self.setWindowTitle(self.dialog_title)
        self.setMinimumWidth(self.min_width)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Group fields by their group attribute
        groups: dict[str, list[FieldDef]] = {}
        ungrouped: list[FieldDef] = []

        for field_def in self.fields:
            if field_def.group:
                if field_def.group not in groups:
                    groups[field_def.group] = []
                groups[field_def.group].append(field_def)
            else:
                ungrouped.append(field_def)

        # Add ungrouped fields first
        if ungrouped:
            form = QFormLayout()
            for field_def in ungrouped:
                widget = self._create_widget(field_def)
                form.addRow(f"{field_def.label}:", widget)
            layout.addLayout(form)

        # Add grouped fields
        for group_name, group_fields in groups.items():
            group_box = QGroupBox(group_name)
            form = QFormLayout(group_box)
            for field_def in group_fields:
                widget = self._create_widget(field_def)
                form.addRow(f"{field_def.label}:", widget)
            layout.addWidget(group_box)

        # Live tune section
        if self.show_live_tune:
            live_layout = QHBoxLayout()
            self._live_tune_check = QCheckBox("Live Tune")
            self._live_tune_check.setToolTip(
                "When enabled, parameter changes are sent to the robot immediately.\n"
                "The robot must be connected and the controller slot configured."
            )
            self._live_tune_check.stateChanged.connect(self._on_live_tune_changed)
            live_layout.addWidget(self._live_tune_check)

            self._live_status = QLabel("")
            self._live_status.setStyleSheet("color: #71717A; font-size: 11px;")
            live_layout.addWidget(self._live_status)
            live_layout.addStretch()

            layout.addLayout(live_layout)

        layout.addStretch()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_widget(self, field_def: FieldDef) -> QWidget:
        """
        Create appropriate widget based on field type.

        Args:
            field_def: Field definition

        Returns:
            Created widget
        """
        value = self._properties.get(field_def.name, field_def.default)

        if field_def.field_type == "float":
            widget = QDoubleSpinBox()
            widget.setRange(field_def.min_val, field_def.max_val)
            widget.setDecimals(field_def.decimals)
            widget.setSingleStep(field_def.step)
            if field_def.suffix:
                widget.setSuffix(f" {field_def.suffix}")
            if value is not None:
                widget.setValue(float(value))
            if field_def.live_update:
                widget.valueChanged.connect(
                    lambda v, name=field_def.name: self._on_value_changed(name, v)
                )

        elif field_def.field_type == "int":
            widget = QSpinBox()
            widget.setRange(int(field_def.min_val), int(field_def.max_val))
            widget.setSingleStep(int(field_def.step) if field_def.step >= 1 else 1)
            if field_def.suffix:
                widget.setSuffix(f" {field_def.suffix}")
            if value is not None:
                widget.setValue(int(value))
            if field_def.live_update:
                widget.valueChanged.connect(
                    lambda v, name=field_def.name: self._on_value_changed(name, v)
                )

        elif field_def.field_type == "bool":
            widget = QCheckBox()
            if value is not None:
                widget.setChecked(bool(value))
            if field_def.live_update:
                widget.stateChanged.connect(
                    lambda s, name=field_def.name: self._on_value_changed(
                        name, s == Qt.Checked.value
                    )
                )

        elif field_def.field_type == "choice":
            widget = QComboBox()
            choices = field_def.choices or []
            widget.addItems(choices)
            if value in choices:
                widget.setCurrentText(str(value))
            if field_def.live_update:
                widget.currentTextChanged.connect(
                    lambda t, name=field_def.name: self._on_value_changed(name, t)
                )

        else:  # str or default
            widget = QLineEdit()
            if value is not None:
                widget.setText(str(value))
            if field_def.live_update:
                widget.textChanged.connect(
                    lambda t, name=field_def.name: self._on_value_changed(name, t)
                )

        if field_def.tooltip:
            widget.setToolTip(field_def.tooltip)

        self._widgets[field_def.name] = widget
        return widget

    def _on_live_tune_changed(self, state: int) -> None:
        """Handle live tune checkbox change."""
        self._live_tune = state == Qt.Checked.value
        if self._live_tune:
            if self._controller and getattr(self._controller, "is_connected", False):
                self._live_status.setText("Connected - changes sent immediately")
                self._live_status.setStyleSheet("color: #22C55E; font-size: 11px;")
            else:
                self._live_status.setText("Not connected - changes will be local only")
                self._live_status.setStyleSheet("color: #F59E0B; font-size: 11px;")
        else:
            self._live_status.setText("")

    def _on_value_changed(self, name: str, value: Any) -> None:
        """Handle value change - send update if live tuning."""
        if not self._live_tune:
            return

        # Emit signal for external handling
        self.live_update.emit(self._slot, {name: value})

        # Direct controller update if available
        if self._controller and getattr(self._controller, "is_connected", False):
            # Try to use controller's param update method
            if hasattr(self._controller, "controller_set_param"):
                self._controller.controller_set_param(self._slot, name, value)

    def set_controller(self, controller: Any) -> None:
        """
        Set the robot controller for live tuning.

        Args:
            controller: RobotController instance
        """
        self._controller = controller
        # Update status if live tune is already enabled
        if self._live_tune:
            self._on_live_tune_changed(Qt.Checked.value)

    def get_values(self) -> dict[str, Any]:
        """
        Get all field values from dialog.

        Returns:
            Dict mapping field names to their current values
        """
        values = {}

        for field_def in self.fields:
            widget = self._widgets.get(field_def.name)
            if widget is None:
                continue

            if field_def.field_type in ("float", "int"):
                values[field_def.name] = widget.value()
            elif field_def.field_type == "bool":
                values[field_def.name] = widget.isChecked()
            elif field_def.field_type == "choice":
                values[field_def.name] = widget.currentText()
            else:
                values[field_def.name] = widget.text()

        return values

    def get_config(self) -> dict[str, Any]:
        """
        Alias for get_values() for compatibility.

        Returns:
            Dict mapping field names to their current values
        """
        return self.get_values()
