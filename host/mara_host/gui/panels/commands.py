# mara_host/gui/panels/commands.py
"""
Commands panel for testing and sending robot commands.
"""

import json

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGroupBox,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QPlainTextEdit,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QScrollArea,
)
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings


class CommandsPanel(QWidget):
    """
    Commands panel for testing and sending commands.

    Layout:
        ┌────────────────────────────┬────────────────────────────┐
        │ Command Tree               │ Parameters                 │
        │ ▼ System                   │ CMD_DC_SET_SPEED           │
        │   CMD_ARM                  │ motor_id: [0 ▼]           │
        │   CMD_DISARM               │ speed: [0.0____]          │
        │ ▼ Motors                   │                            │
        │   CMD_DC_SET_SPEED ←       │ [Send Command]             │
        │   CMD_DC_STOP              │                            │
        ├────────────────────────────┼────────────────────────────┤
        │ Response                   │ History                    │
        │ {"ok": true, "seq": 42}    │ 12:34 CMD_ARM → OK        │
        └────────────────────────────┴────────────────────────────┘
    """

    def __init__(
        self,
        signals: GuiSignals,
        controller: RobotController,
        settings: GuiSettings,
    ):
        super().__init__()

        self.signals = signals
        self.controller = controller
        self.settings = settings

        self._current_command = None
        self._param_widgets = {}

        self._setup_ui()
        self._setup_connections()
        self._load_commands()

    def _setup_ui(self) -> None:
        """Set up the commands panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left: Command tree
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Commands"))

        self.command_tree = QTreeWidget()
        self.command_tree.setHeaderHidden(True)
        self.command_tree.itemClicked.connect(self._on_command_selected)
        left_layout.addWidget(self.command_tree)

        splitter.addWidget(left_widget)

        # Right: Parameters and response
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Parameters section
        params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout(params_group)

        self.cmd_name_label = QLabel("Select a command")
        self.cmd_name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        params_layout.addWidget(self.cmd_name_label)

        self.cmd_desc_label = QLabel("")
        self.cmd_desc_label.setStyleSheet("color: #B0B0C0;")
        self.cmd_desc_label.setWordWrap(True)
        params_layout.addWidget(self.cmd_desc_label)

        # Scrollable param form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        self.param_form_widget = QWidget()
        self.param_form = QFormLayout(self.param_form_widget)
        self.param_form.setSpacing(8)
        scroll.setWidget(self.param_form_widget)

        params_layout.addWidget(scroll, 1)

        # Send button
        self.send_btn = QPushButton("Send Command")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self._send_command)
        params_layout.addWidget(self.send_btn)

        right_layout.addWidget(params_group, 1)

        # Response section
        response_group = QGroupBox("Response")
        response_layout = QVBoxLayout(response_group)

        self.response_text = QPlainTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setMaximumHeight(150)
        response_layout.addWidget(self.response_text)

        right_layout.addWidget(response_group)

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter)

    def _setup_connections(self) -> None:
        """Connect signals."""
        self.signals.command_ack.connect(self._on_command_ack)
        self.signals.connection_changed.connect(self._on_connection_changed)

    def _load_commands(self) -> None:
        """Load commands from schema."""
        try:
            from mara_host.config.commands import load_commands

            self.commands = load_commands()
            self._populate_tree()
        except Exception as e:
            # Fallback to basic commands
            self.commands = self._get_basic_commands()
            self._populate_tree()

    def _get_basic_commands(self) -> dict:
        """Get basic command definitions."""
        return {
            "CMD_ARM": {"description": "Arm the robot", "payload": {}},
            "CMD_DISARM": {"description": "Disarm the robot", "payload": {}},
            "CMD_ACTIVATE": {"description": "Activate motion", "payload": {}},
            "CMD_DEACTIVATE": {"description": "Deactivate motion", "payload": {}},
            "CMD_ESTOP": {"description": "Emergency stop", "payload": {}},
            "CMD_STOP": {"description": "Stop all motion", "payload": {}},
            "CMD_LED_ON": {"description": "Turn LED on", "payload": {}},
            "CMD_LED_OFF": {"description": "Turn LED off", "payload": {}},
            "CMD_DC_SET_SPEED": {
                "description": "Set DC motor speed",
                "payload": {
                    "motor_id": {"type": "int", "required": True},
                    "speed": {"type": "float", "required": True, "min": -1, "max": 1},
                },
            },
            "CMD_GPIO_WRITE": {
                "description": "Write GPIO value",
                "payload": {
                    "channel": {"type": "int", "required": True},
                    "value": {"type": "int", "required": True},
                },
            },
        }

    def _populate_tree(self) -> None:
        """Populate the command tree."""
        self.command_tree.clear()

        # Group commands by category
        categories = {
            "System": [],
            "Motors": [],
            "Servos": [],
            "GPIO": [],
            "Sensors": [],
            "Telemetry": [],
            "Camera": [],
            "Control": [],
            "Other": [],
        }

        for cmd_name in sorted(self.commands.keys()):
            if cmd_name.startswith("CMD_ARM") or cmd_name.startswith("CMD_DISARM") or \
               cmd_name.startswith("CMD_ESTOP") or cmd_name.startswith("CMD_STOP") or \
               cmd_name.startswith("CMD_ACTIVATE") or cmd_name.startswith("CMD_DEACTIVATE"):
                categories["System"].append(cmd_name)
            elif "DC" in cmd_name or "STEPPER" in cmd_name:
                categories["Motors"].append(cmd_name)
            elif "SERVO" in cmd_name:
                categories["Servos"].append(cmd_name)
            elif "GPIO" in cmd_name or "LED" in cmd_name or "PWM" in cmd_name:
                categories["GPIO"].append(cmd_name)
            elif "ENCODER" in cmd_name or "IMU" in cmd_name or "ULTRA" in cmd_name:
                categories["Sensors"].append(cmd_name)
            elif "TELEM" in cmd_name:
                categories["Telemetry"].append(cmd_name)
            elif "CAM" in cmd_name:
                categories["Camera"].append(cmd_name)
            elif "CTRL" in cmd_name or "OBSERVER" in cmd_name:
                categories["Control"].append(cmd_name)
            else:
                categories["Other"].append(cmd_name)

        # Build tree
        for category, cmds in categories.items():
            if not cmds:
                continue

            cat_item = QTreeWidgetItem([category])
            cat_item.setExpanded(True)

            for cmd_name in cmds:
                cmd_item = QTreeWidgetItem([cmd_name])
                cmd_item.setData(0, Qt.UserRole, cmd_name)
                cat_item.addChild(cmd_item)

            self.command_tree.addTopLevelItem(cat_item)

    def _on_command_selected(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle command selection."""
        cmd_name = item.data(0, Qt.UserRole)
        if not cmd_name:
            return

        self._current_command = cmd_name
        cmd_def = self.commands.get(cmd_name, {})

        self.cmd_name_label.setText(cmd_name)
        self.cmd_desc_label.setText(cmd_def.get("description", ""))

        # Clear old params
        while self.param_form.rowCount() > 0:
            self.param_form.removeRow(0)
        self._param_widgets.clear()

        # Add param fields
        payload = cmd_def.get("payload", {})
        for param_name, param_def in payload.items():
            widget = self._create_param_widget(param_name, param_def)
            if widget:
                self._param_widgets[param_name] = widget
                self.param_form.addRow(f"{param_name}:", widget)

        self.send_btn.setEnabled(self.controller.is_connected)

    def _create_param_widget(self, name: str, param_def: dict) -> QWidget:
        """Create a widget for a parameter."""
        param_type = param_def.get("type", "string")

        if param_type == "int" or param_type == "integer":
            widget = QSpinBox()
            widget.setRange(
                param_def.get("min", -1000000),
                param_def.get("max", 1000000)
            )
            widget.setValue(param_def.get("default", 0))
            return widget

        elif param_type == "float":
            widget = QDoubleSpinBox()
            widget.setRange(
                param_def.get("min", -1000000),
                param_def.get("max", 1000000)
            )
            widget.setDecimals(3)
            widget.setValue(param_def.get("default", 0.0))
            return widget

        elif param_type == "bool":
            widget = QCheckBox()
            widget.setChecked(param_def.get("default", False))
            return widget

        else:
            widget = QLineEdit()
            widget.setText(str(param_def.get("default", "")))
            return widget

    def _send_command(self) -> None:
        """Send the current command."""
        if not self._current_command:
            return

        # Build payload
        payload = {}
        for param_name, widget in self._param_widgets.items():
            if isinstance(widget, QSpinBox):
                payload[param_name] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                payload[param_name] = widget.value()
            elif isinstance(widget, QCheckBox):
                payload[param_name] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                payload[param_name] = widget.text()

        # Send
        self.response_text.clear()
        self.response_text.appendPlainText(
            f"Sending: {self._current_command}\n"
            f"Payload: {json.dumps(payload, indent=2)}"
        )

        def on_response(ok: bool, result: str):
            self.response_text.appendPlainText(
                f"\nResult: {'OK' if ok else 'FAILED'}"
                f"\n{result}"
            )

        self.controller.send_command(self._current_command, payload, on_response)

    def _on_command_ack(self, seq: int, ok: bool, error: str) -> None:
        """Handle command acknowledgment."""
        pass  # Handled by callback

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        """Handle connection state change."""
        self.send_btn.setEnabled(connected and self._current_command is not None)
