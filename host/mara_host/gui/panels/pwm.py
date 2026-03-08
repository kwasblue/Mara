# mara_host/gui/panels/pwm.py
"""
PWM Control Panel.

Direct control of PWM channels with frequency and duty cycle adjustment.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "pwm",
    "label": "PWM",
    "order": 25,
}

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QScrollArea,
    QFrame,
    QCheckBox,
)
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings


class PWMChannelWidget(QFrame):
    """Widget for controlling a single PWM channel."""

    def __init__(
        self,
        channel: int,
        controller: RobotController,
        parent=None,
    ):
        super().__init__(parent)
        self.channel = channel
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
        self.title_label = QLabel(f"PWM Channel {self.channel}")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #FAFAFA;")
        header.addWidget(self.title_label)

        self.enable_check = QCheckBox("Enable")
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        header.addWidget(self.enable_check)
        header.addStretch()
        layout.addLayout(header)

        # Frequency
        freq_row = QHBoxLayout()
        freq_row.addWidget(QLabel("Frequency:"))
        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(1, 40000)
        self.freq_spin.setValue(1000)
        self.freq_spin.setSuffix(" Hz")
        self.freq_spin.valueChanged.connect(self._on_freq_changed)
        freq_row.addWidget(self.freq_spin)

        # Preset frequencies
        for freq in [100, 1000, 5000, 20000]:
            btn = QPushButton(f"{freq//1000}k" if freq >= 1000 else str(freq))
            btn.setObjectName("secondary")
            btn.setMaximumWidth(50)
            btn.clicked.connect(lambda _, f=freq: self.freq_spin.setValue(f))
            freq_row.addWidget(btn)

        freq_row.addStretch()
        layout.addLayout(freq_row)

        # Duty cycle slider
        duty_layout = QHBoxLayout()
        duty_layout.addWidget(QLabel("Duty:"))

        self.duty_slider = QSlider(Qt.Orientation.Horizontal)
        self.duty_slider.setRange(0, 100)
        self.duty_slider.setValue(0)
        self.duty_slider.valueChanged.connect(self._on_duty_changed)
        duty_layout.addWidget(self.duty_slider, 1)

        self.duty_label = QLabel("0%")
        self.duty_label.setMinimumWidth(50)
        self.duty_label.setStyleSheet("font-weight: bold;")
        duty_layout.addWidget(self.duty_label)

        layout.addLayout(duty_layout)

        # Quick duty buttons
        btn_row = QHBoxLayout()
        for pct in [0, 25, 50, 75, 100]:
            btn = QPushButton(f"{pct}%")
            btn.setObjectName("secondary")
            btn.setMaximumWidth(50)
            btn.clicked.connect(lambda _, p=pct: self._set_duty(p))
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_enable_changed(self, state: int) -> None:
        self._enabled = state == Qt.CheckState.Checked.value
        if self._enabled:
            self._send_pwm()
        else:
            # Stop PWM
            self.controller.send_command(
                "CMD_PWM_SET",
                {"channel": self.channel, "duty": 0.0}
            )

    def _on_freq_changed(self, value: int) -> None:
        if self._enabled:
            self._send_pwm()

    def _on_duty_changed(self, value: int) -> None:
        self.duty_label.setText(f"{value}%")
        if self._enabled:
            self._send_pwm()

    def _set_duty(self, percent: int) -> None:
        self.duty_slider.setValue(percent)

    def _send_pwm(self) -> None:
        duty = self.duty_slider.value() / 100.0
        freq = self.freq_spin.value()
        self.controller.send_command(
            "CMD_PWM_SET",
            {"channel": self.channel, "duty": duty, "freq_hz": freq}
        )


class PWMPanel(QWidget):
    """PWM Control Panel."""

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

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Header
        header = QLabel("PWM Channel Control")
        header.setStyleSheet("font-weight: bold; font-size: 16px; color: #FAFAFA;")
        layout.addWidget(header)

        info = QLabel("Control PWM duty cycle and frequency for each channel.")
        info.setStyleSheet("color: #71717A;")
        layout.addWidget(info)

        # PWM channels
        self.channel_widgets: dict[int, PWMChannelWidget] = {}
        for ch in range(4):
            widget = PWMChannelWidget(ch, self.controller)
            self.channel_widgets[ch] = widget
            layout.addWidget(widget)

        # All stop button
        stop_all_btn = QPushButton("Stop All PWM")
        stop_all_btn.setObjectName("danger")
        stop_all_btn.clicked.connect(self._stop_all)
        layout.addWidget(stop_all_btn)

        layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _setup_connections(self) -> None:
        self.signals.connection_changed.connect(self._on_connection_changed)

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        for widget in self.channel_widgets.values():
            widget.setEnabled(connected)

    def _stop_all(self) -> None:
        for ch, widget in self.channel_widgets.items():
            widget.duty_slider.setValue(0)
            widget.enable_check.setChecked(False)
            self.controller.send_command(
                "CMD_PWM_SET",
                {"channel": ch, "duty": 0.0}
            )
