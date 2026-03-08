# mara_host/gui/panels/stepper.py
"""
Stepper Motor Control Panel.

Direct control of stepper motors with step/degree/revolution modes.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "stepper",
    "label": "Stepper",
    "order": 26,
}

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QScrollArea,
    QFrame,
    QCheckBox,
    QProgressBar,
)
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings


class StepperWidget(QFrame):
    """Widget for controlling a single stepper motor."""

    def __init__(
        self,
        stepper_id: int,
        controller: RobotController,
        parent=None,
    ):
        super().__init__(parent)
        self.stepper_id = stepper_id
        self.controller = controller
        self._enabled = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { background-color: #1A1A1C; border-radius: 8px; padding: 12px; }"
        )

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        self.title_label = QLabel(f"Stepper {self.stepper_id}")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #FAFAFA;")
        header.addWidget(self.title_label)

        self.enable_check = QCheckBox("Enable")
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        header.addWidget(self.enable_check)
        header.addStretch()

        self.status_label = QLabel("Disabled")
        self.status_label.setStyleSheet("color: #71717A;")
        header.addWidget(self.status_label)
        layout.addLayout(header)

        # Position display
        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("Position:"))
        self.position_label = QLabel("0 steps")
        self.position_label.setStyleSheet("font-weight: bold; color: #22C55E;")
        pos_row.addWidget(self.position_label)
        pos_row.addStretch()

        reset_btn = QPushButton("Reset Position")
        reset_btn.setObjectName("secondary")
        reset_btn.clicked.connect(self._reset_position)
        pos_row.addWidget(reset_btn)
        layout.addLayout(pos_row)

        # Movement mode selector
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Steps", "Degrees", "Revolutions"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Movement input
        move_row = QHBoxLayout()
        move_row.addWidget(QLabel("Amount:"))

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(-10000, 10000)
        self.amount_spin.setValue(0)
        self.amount_spin.setDecimals(2)
        move_row.addWidget(self.amount_spin)

        self.unit_label = QLabel("steps")
        self.unit_label.setMinimumWidth(80)
        move_row.addWidget(self.unit_label)

        move_row.addStretch()
        layout.addLayout(move_row)

        # Speed
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed:"))
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.01, 10.0)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setSuffix(" RPS")
        speed_row.addWidget(self.speed_spin)
        speed_row.addStretch()
        layout.addLayout(speed_row)

        # Movement buttons
        btn_row = QHBoxLayout()

        self.move_btn = QPushButton("Move")
        self.move_btn.setObjectName("primary")
        self.move_btn.clicked.connect(self._move)
        btn_row.addWidget(self.move_btn)

        # Quick move buttons
        for amount in [-90, -10, 10, 90]:
            sign = "+" if amount > 0 else ""
            btn = QPushButton(f"{sign}{amount}")
            btn.setObjectName("secondary")
            btn.setMaximumWidth(50)
            btn.clicked.connect(lambda _, a=amount: self._quick_move(a))
            btn_row.addWidget(btn)

        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(self.stop_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_enable_changed(self, state: int) -> None:
        self._enabled = state == Qt.CheckState.Checked.value
        self.controller.send_command(
            "CMD_STEPPER_ENABLE",
            {"stepper_id": self.stepper_id, "enable": self._enabled}
        )
        self.status_label.setText("Enabled" if self._enabled else "Disabled")
        self.status_label.setStyleSheet(
            "color: #22C55E;" if self._enabled else "color: #71717A;"
        )

    def _on_mode_changed(self, index: int) -> None:
        units = ["steps", "degrees", "revolutions"]
        self.unit_label.setText(units[index])

        # Adjust range and step based on mode
        if index == 0:  # Steps
            self.amount_spin.setRange(-10000, 10000)
            self.amount_spin.setDecimals(0)
            self.amount_spin.setSingleStep(1)
        elif index == 1:  # Degrees
            self.amount_spin.setRange(-3600, 3600)
            self.amount_spin.setDecimals(1)
            self.amount_spin.setSingleStep(1)
        else:  # Revolutions
            self.amount_spin.setRange(-100, 100)
            self.amount_spin.setDecimals(2)
            self.amount_spin.setSingleStep(0.25)

    def _move(self) -> None:
        if not self._enabled:
            self.enable_check.setChecked(True)

        mode = self.mode_combo.currentIndex()
        amount = self.amount_spin.value()
        speed = self.speed_spin.value()

        if mode == 0:  # Steps
            self.controller.send_command(
                "CMD_STEPPER_MOVE_REL",
                {"stepper_id": self.stepper_id, "steps": int(amount), "speed_rps": speed}
            )
        elif mode == 1:  # Degrees
            self.controller.send_command(
                "CMD_STEPPER_MOVE_DEG",
                {"stepper_id": self.stepper_id, "degrees": amount, "speed_rps": speed}
            )
        else:  # Revolutions
            self.controller.send_command(
                "CMD_STEPPER_MOVE_REV",
                {"stepper_id": self.stepper_id, "revolutions": amount, "speed_rps": speed}
            )

    def _quick_move(self, amount: int) -> None:
        """Quick move by degrees."""
        if not self._enabled:
            self.enable_check.setChecked(True)

        speed = self.speed_spin.value()
        self.controller.send_command(
            "CMD_STEPPER_MOVE_DEG",
            {"stepper_id": self.stepper_id, "degrees": amount, "speed_rps": speed}
        )

    def _stop(self) -> None:
        self.controller.send_command(
            "CMD_STEPPER_STOP",
            {"stepper_id": self.stepper_id}
        )

    def _reset_position(self) -> None:
        self.controller.send_command(
            "CMD_STEPPER_RESET_POS",
            {"stepper_id": self.stepper_id}
        )
        self.position_label.setText("0 steps")


class StepperPanel(QWidget):
    """Stepper Motor Control Panel."""

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

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Header
        header = QLabel("Stepper Motor Control")
        header.setStyleSheet("font-weight: bold; font-size: 16px; color: #FAFAFA;")
        layout.addWidget(header)

        info = QLabel("Control stepper motors by steps, degrees, or revolutions.")
        info.setStyleSheet("color: #71717A;")
        layout.addWidget(info)

        # Stepper widgets
        self.stepper_widgets: dict[int, StepperWidget] = {}
        for stepper_id in range(4):
            widget = StepperWidget(stepper_id, self.controller)
            self.stepper_widgets[stepper_id] = widget
            layout.addWidget(widget)

        # Stop all button
        stop_all_btn = QPushButton("STOP ALL STEPPERS")
        stop_all_btn.setObjectName("danger")
        stop_all_btn.setMinimumHeight(44)
        stop_all_btn.clicked.connect(self._stop_all)
        layout.addWidget(stop_all_btn)

        layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _setup_connections(self) -> None:
        self.signals.connection_changed.connect(self._on_connection_changed)

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        for widget in self.stepper_widgets.values():
            widget.setEnabled(connected)

    def _stop_all(self) -> None:
        for stepper_id, widget in self.stepper_widgets.items():
            self.controller.send_command(
                "CMD_STEPPER_STOP",
                {"stepper_id": stepper_id}
            )
