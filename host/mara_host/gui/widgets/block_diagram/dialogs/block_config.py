# mara_host/gui/widgets/block_diagram/dialogs/block_config.py
"""Base configuration dialog for blocks."""

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QWidget,
)


class BlockConfigDialog(QDialog):
    """
    Base configuration dialog for blocks.

    Can be used directly for simple blocks or subclassed
    for more complex configuration needs.
    """

    def __init__(
        self,
        properties: dict[str, Any],
        schema: dict[str, dict] = None,
        title: str = "Block Configuration",
        parent=None,
    ):
        """
        Initialize dialog.

        Args:
            properties: Current block properties
            schema: Optional schema defining fields:
                {
                    "field_name": {
                        "type": "int" | "float" | "str" | "bool" | "choice",
                        "label": "Display Label",
                        "min": 0,          # For numeric
                        "max": 100,        # For numeric
                        "decimals": 2,     # For float
                        "choices": [...],  # For choice type
                        "group": "Group Name",  # Optional grouping
                    }
                }
            title: Dialog title
            parent: Parent widget
        """
        super().__init__(parent)
        self._properties = properties.copy()
        self._schema = schema or self._infer_schema(properties)
        self._widgets: dict[str, QWidget] = {}

        self.setWindowTitle(title)
        self.setMinimumWidth(300)
        self._setup_ui()

    def _infer_schema(self, properties: dict) -> dict:
        """Infer schema from property types."""
        schema = {}
        for key, value in properties.items():
            if key.startswith("_"):
                continue  # Skip private properties

            field = {"label": key.replace("_", " ").title()}

            if isinstance(value, bool):
                field["type"] = "bool"
            elif isinstance(value, int):
                field["type"] = "int"
                field["min"] = -10000
                field["max"] = 10000
            elif isinstance(value, float):
                field["type"] = "float"
                field["min"] = -10000.0
                field["max"] = 10000.0
                field["decimals"] = 4
            elif isinstance(value, str):
                field["type"] = "str"
            elif isinstance(value, list):
                continue  # Skip lists for auto-inference
            else:
                continue

            schema[key] = field

        return schema

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Group fields
        groups: dict[str, list[tuple[str, dict]]] = {}
        ungrouped = []

        for field_name, field_config in self._schema.items():
            group = field_config.get("group", "")
            if group:
                if group not in groups:
                    groups[group] = []
                groups[group].append((field_name, field_config))
            else:
                ungrouped.append((field_name, field_config))

        # Add ungrouped fields first
        if ungrouped:
            form = QFormLayout()
            for field_name, field_config in ungrouped:
                widget = self._create_field_widget(field_name, field_config)
                form.addRow(field_config.get("label", field_name) + ":", widget)
            layout.addLayout(form)

        # Add grouped fields
        for group_name, fields in groups.items():
            group_box = QGroupBox(group_name)
            form = QFormLayout(group_box)
            for field_name, field_config in fields:
                widget = self._create_field_widget(field_name, field_config)
                form.addRow(field_config.get("label", field_name) + ":", widget)
            layout.addWidget(group_box)

        layout.addStretch()

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_field_widget(self, field_name: str, config: dict) -> QWidget:
        """Create appropriate widget for field type."""
        field_type = config.get("type", "str")
        value = self._properties.get(field_name)

        if field_type == "int":
            widget = QSpinBox()
            widget.setRange(config.get("min", -10000), config.get("max", 10000))
            if value is not None:
                widget.setValue(int(value))
            if "suffix" in config:
                widget.setSuffix(config["suffix"])

        elif field_type == "float":
            widget = QDoubleSpinBox()
            widget.setRange(config.get("min", -10000.0), config.get("max", 10000.0))
            widget.setDecimals(config.get("decimals", 4))
            if value is not None:
                widget.setValue(float(value))
            if "suffix" in config:
                widget.setSuffix(config["suffix"])

        elif field_type == "bool":
            widget = QCheckBox()
            if value is not None:
                widget.setChecked(bool(value))

        elif field_type == "choice":
            widget = QComboBox()
            choices = config.get("choices", [])
            widget.addItems(choices)
            if value in choices:
                widget.setCurrentText(str(value))

        else:  # str or default
            widget = QLineEdit()
            if value is not None:
                widget.setText(str(value))

        self._widgets[field_name] = widget
        return widget

    def get_config(self) -> dict[str, Any]:
        """Get configuration values from dialog."""
        config = {}

        for field_name, widget in self._widgets.items():
            field_type = self._schema.get(field_name, {}).get("type", "str")

            if field_type == "int":
                config[field_name] = widget.value()
            elif field_type == "float":
                config[field_name] = widget.value()
            elif field_type == "bool":
                config[field_name] = widget.isChecked()
            elif field_type == "choice":
                config[field_name] = widget.currentText()
            else:
                config[field_name] = widget.text()

        return config
