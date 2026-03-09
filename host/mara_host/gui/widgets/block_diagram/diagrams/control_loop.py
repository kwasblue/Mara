# mara_host/gui/widgets/block_diagram/diagrams/control_loop.py
"""Control loop diagram view."""

import uuid

from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QPushButton,
    QCheckBox,
    QFrame,
    QMessageBox,
    QMenu,
)

from ..core.canvas import DiagramCanvas
from ..core.models import DiagramState
from ..blocks.pid import PIDBlock
from ..blocks.observer import ObserverBlock
from ..blocks.signal import (
    SignalSourceBlock,
    SignalSinkBlock,
    SumBlock,
    GainBlock,
    IntegratorBlock,
    DerivativeBlock,
    SaturationBlock,
    FilterBlock,
    DelayBlock,
)
from ..blocks.service import MotorServiceBlock, ServoServiceBlock, GPIOServiceBlock
from .palette import ComponentPalette


class ControlLoopDiagram(QWidget):
    """
    Control Loop diagram view.

    Shows PID controllers, observers, and signal flow between components.
    Used to visualize and configure the control system architecture.

    Signals:
        diagram_changed(): Emitted when diagram state changes
        block_configured(str, dict): Emitted when a block is configured
        controller_sync_requested(str, dict): Request sync to firmware
    """

    diagram_changed = Signal()
    block_configured = Signal(str, dict)
    controller_sync_requested = Signal(str, dict)  # block_id, config

    def __init__(self, parent=None):
        super().__init__(parent)
        self._controller = None
        self._auto_sync = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #1F1F23; border-bottom: 1px solid #27272A;")
        toolbar.setFixedHeight(44)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Control Loop")
        title.setStyleSheet("font-weight: 600; color: #FAFAFA;")
        toolbar_layout.addWidget(title)

        toolbar_layout.addStretch()

        # Quick add buttons
        self.add_pid_btn = QPushButton("+ PID")
        self.add_pid_btn.setObjectName("secondary")
        self.add_pid_btn.clicked.connect(lambda: self._quick_add("pid"))
        toolbar_layout.addWidget(self.add_pid_btn)

        self.add_observer_btn = QPushButton("+ Observer")
        self.add_observer_btn.setObjectName("secondary")
        self.add_observer_btn.clicked.connect(lambda: self._quick_add("observer"))
        toolbar_layout.addWidget(self.add_observer_btn)

        # Examples dropdown
        self.examples_btn = QPushButton("Examples")
        self.examples_btn.setObjectName("secondary")
        examples_menu = QMenu(self)
        examples_menu.addAction("Basic PID Loop", self._load_basic_pid_example)
        examples_menu.addAction("Servo Position Control", self._load_servo_example)
        examples_menu.addAction("Motor with Encoder Feedback", self._load_encoder_feedback_example)
        examples_menu.addAction("Cascaded PID", self._load_cascaded_pid_example)
        self.examples_btn.setMenu(examples_menu)
        toolbar_layout.addWidget(self.examples_btn)

        # Sync button
        # Auto-sync checkbox
        self.auto_sync_check = QCheckBox("Auto")
        self.auto_sync_check.setToolTip("Automatically sync to robot when diagram changes")
        self.auto_sync_check.setStyleSheet("color: #FAFAFA;")
        self.auto_sync_check.stateChanged.connect(self._on_auto_sync_changed)
        toolbar_layout.addWidget(self.auto_sync_check)

        self.sync_btn = QPushButton("Sync to Robot")
        self.sync_btn.setObjectName("primary")
        self.sync_btn.clicked.connect(self._sync_to_robot)
        toolbar_layout.addWidget(self.sync_btn)

        self.zoom_fit_btn = QPushButton("Fit")
        self.zoom_fit_btn.setObjectName("flat")
        self.zoom_fit_btn.clicked.connect(self._zoom_to_fit)
        toolbar_layout.addWidget(self.zoom_fit_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("flat")
        self.clear_btn.clicked.connect(self._clear_diagram)
        toolbar_layout.addWidget(self.clear_btn)

        layout.addWidget(toolbar)

        # Main content with splitter
        splitter = QSplitter(Qt.Horizontal)

        # Component palette
        self.palette = ComponentPalette(palette_type="control")
        splitter.addWidget(self.palette)

        # Canvas
        self.canvas = DiagramCanvas()
        self.canvas.setAcceptDrops(True)
        self.canvas.dragEnterEvent = self._canvas_drag_enter
        self.canvas.dragMoveEvent = self._canvas_drag_move
        self.canvas.dragLeaveEvent = self._canvas_drag_leave
        self.canvas.dropEvent = self._canvas_drop
        splitter.addWidget(self.canvas)

        # Set splitter sizes
        splitter.setSizes([200, 600])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.canvas.diagram_changed.connect(self._on_diagram_changed)
        self.canvas.block_configured.connect(self._on_block_configured)
        self.canvas.block_double_clicked.connect(self._on_block_double_clicked)

    def _on_diagram_changed(self) -> None:
        """Handle diagram change - trigger auto-sync if enabled."""
        self.diagram_changed.emit()
        if self._auto_sync and self._controller:
            self._sync_to_robot(silent=True)

    def set_controller(self, controller) -> None:
        """Set the robot controller for syncing."""
        self._controller = controller

    def _on_auto_sync_changed(self, state: int) -> None:
        """Handle auto-sync checkbox change."""
        self._auto_sync = state == Qt.Checked.value
        if self._auto_sync and self._controller:
            # Perform initial sync when enabling auto-sync
            self._sync_to_robot(silent=True)

    def _quick_add(self, block_type: str) -> None:
        """Quick add a block to center of canvas."""
        center = QPointF(
            self.canvas.width() / 2,
            self.canvas.height() / 2,
        )
        pos = self.canvas.canvas_to_scene(center)
        pos = self.canvas._grid.snap(pos)
        self._create_block(block_type, pos)

    def _zoom_to_fit(self) -> None:
        """Zoom to fit all blocks."""
        self.canvas.zoom_to_fit()

    def _clear_diagram(self) -> None:
        """Clear the diagram."""
        reply = QMessageBox.question(
            self,
            "Clear Diagram",
            "Are you sure you want to clear all blocks?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.canvas.clear()

    def _sync_to_robot(self, silent: bool = False) -> None:
        """
        Sync control configuration to robot.

        Args:
            silent: If True, don't show message boxes (for auto-sync)
        """
        if not self._controller:
            if not silent:
                QMessageBox.warning(
                    self,
                    "Not Connected",
                    "Connect to a robot first to sync control configuration.",
                )
            return

        from ..core.block_mapping import map_diagram_to_firmware

        # Get diagram state and map to firmware configs
        state = self.get_state()
        state_dict = state.to_dict() if hasattr(state, 'to_dict') else {
            "blocks": [{"block_type": b.block_type, "properties": b.config.properties}
                       for b in self.canvas.get_blocks()]
        }

        controller_configs, observer_configs, warnings = map_diagram_to_firmware(state_dict)

        # Show warnings if any (skip in silent mode)
        if warnings and not silent:
            warning_text = "\n".join(f"- {w}" for w in warnings)
            QMessageBox.warning(
                self,
                "Mapping Warnings",
                f"Some blocks have limited firmware support:\n\n{warning_text}",
            )

        # Sync controller slots
        synced_controllers = 0
        for config in controller_configs:
            slot = config["slot"]
            try:
                if config["controller_type"] == "PID":
                    self._controller.controller_config(slot, {
                        "type": "PID",
                        "kp": config["kp"],
                        "ki": config["ki"],
                        "kd": config["kd"],
                        "output_min": config["out_min"],
                        "output_max": config["out_max"],
                    })
                else:  # STATE_SPACE
                    self._controller.controller_config(slot, {
                        "type": "STATE_SPACE",
                        "num_states": config["num_states"],
                        "num_inputs": config["num_inputs"],
                    })
                    # Upload matrices
                    if config.get("A"):
                        self._controller.controller_set_param_array(slot, "A", config["A"])
                    if config.get("B"):
                        self._controller.controller_set_param_array(slot, "B", config["B"])
                    if config.get("C"):
                        self._controller.controller_set_param_array(slot, "C", config["C"])
                    if config.get("K"):
                        self._controller.controller_set_param_array(slot, "K", config["K"])

                synced_controllers += 1
                self.controller_sync_requested.emit(f"slot_{slot}", config)

            except Exception as e:
                if not silent:
                    QMessageBox.warning(
                        self,
                        "Sync Error",
                        f"Failed to sync controller slot {slot}: {e}",
                    )

        # Sync observer slots
        synced_observers = 0
        for config in observer_configs:
            slot = config["slot"]
            try:
                self._controller.observer_config(slot, {
                    "num_states": config["num_states"],
                    "num_inputs": config["num_inputs"],
                    "num_outputs": config["num_outputs"],
                    "rate_hz": config["rate_hz"],
                })
                # Upload matrices
                if config.get("A"):
                    self._controller.observer_set_param_array(slot, "A", config["A"])
                if config.get("B"):
                    self._controller.observer_set_param_array(slot, "B", config["B"])
                if config.get("C"):
                    self._controller.observer_set_param_array(slot, "C", config["C"])
                if config.get("L"):
                    self._controller.observer_set_param_array(slot, "L", config["L"])

                synced_observers += 1

            except Exception as e:
                if not silent:
                    QMessageBox.warning(
                        self,
                        "Sync Error",
                        f"Failed to sync observer slot {slot}: {e}",
                    )

        if not silent:
            QMessageBox.information(
                self,
                "Sync Complete",
                f"Synced {synced_controllers} controller(s) and {synced_observers} observer(s) to robot.",
            )

    def _canvas_drag_enter(self, event) -> None:
        """Handle drag enter on canvas."""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.canvas._drop_preview_pos = self.canvas.canvas_to_scene(event.position())
            self.canvas.update()

    def _canvas_drag_move(self, event) -> None:
        """Handle drag move over canvas - update preview position."""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.canvas._drop_preview_pos = self.canvas._grid.snap(
                self.canvas.canvas_to_scene(event.position())
            )
            self.canvas.update()

    def _canvas_drag_leave(self, event) -> None:
        """Handle drag leave canvas - clear preview."""
        self.canvas._drop_preview_pos = None
        self.canvas.update()

    def _canvas_drop(self, event) -> None:
        """Handle drop on canvas."""
        component_type = event.mimeData().text()
        pos = self.canvas.canvas_to_scene(event.position())
        pos = self.canvas._grid.snap(pos)

        self._create_block(component_type, pos)
        self.canvas._drop_preview_pos = None
        event.acceptProposedAction()
        self.canvas.update()

    def _create_block(self, component_type: str, pos: QPointF) -> None:
        """Create a block of the given type at the position."""
        block_id = f"{component_type}_{uuid.uuid4().hex[:6]}"
        block = None

        if component_type == "pid":
            # Count existing PIDs to assign slot
            pid_count = sum(1 for b in self.canvas.get_blocks() if b.block_type == "pid")
            block = PIDBlock(block_id, f"PID {pid_count}", slot=pid_count)

        elif component_type == "observer":
            observer_count = sum(1 for b in self.canvas.get_blocks() if b.block_type == "observer")
            block = ObserverBlock(block_id, f"Observer {observer_count}", slot=observer_count)

        elif component_type == "signal_source":
            signal_count = sum(1 for b in self.canvas.get_blocks()
                             if b.block_type in ("signal_source", "signal_sink"))
            block = SignalSourceBlock(block_id, f"Ref", signal_id=signal_count)

        elif component_type == "signal_sink":
            signal_count = sum(1 for b in self.canvas.get_blocks()
                             if b.block_type in ("signal_source", "signal_sink"))
            block = SignalSinkBlock(block_id, f"Out", signal_id=signal_count)

        elif component_type == "sum":
            block = SumBlock(block_id)

        elif component_type == "gain":
            block = GainBlock(block_id)

        elif component_type == "motor_service":
            block = MotorServiceBlock(block_id)

        elif component_type == "servo_service":
            block = ServoServiceBlock(block_id)

        elif component_type == "gpio_service":
            block = GPIOServiceBlock(block_id)

        elif component_type == "integrator":
            block = IntegratorBlock(block_id)

        elif component_type == "derivative":
            block = DerivativeBlock(block_id)

        elif component_type == "saturation":
            block = SaturationBlock(block_id)

        elif component_type == "filter":
            block = FilterBlock(block_id)

        elif component_type == "delay":
            block = DelayBlock(block_id)

        if block:
            block.position = pos
            self.canvas.add_block(block)

    def _on_block_double_clicked(self, block_id: str) -> None:
        """Handle block double-click."""
        block = self.canvas.get_block(block_id)
        if block:
            dialog = block.get_config_dialog(self)
            if dialog:
                # Pass controller for live tuning if available
                if hasattr(dialog, "set_controller") and self._controller:
                    dialog.set_controller(self._controller)

                if dialog.exec():
                    if hasattr(dialog, "get_config"):
                        config = dialog.get_config()
                        block.apply_config(config)
                        self.block_configured.emit(block_id, config)
                        self.canvas.update()

    def _on_block_configured(self, block_id: str, config: dict) -> None:
        """Handle block configuration change."""
        self.block_configured.emit(block_id, config)

    def get_state(self) -> DiagramState:
        """Get current diagram state."""
        state = self.canvas.get_state()
        state.diagram_type = "control"
        return state

    def load_state(self, state: DiagramState) -> None:
        """Load diagram state."""
        self.canvas.clear()
        self.diagram_changed.emit()

    # ==================== Example Diagrams ====================

    def _load_basic_pid_example(self) -> None:
        """Load a basic PID control loop example."""
        self.canvas.clear()

        # Signal source (reference/setpoint)
        ref = SignalSourceBlock("ref_0", "Setpoint", signal_id=0)
        ref.position = QPointF(50, 150)
        self.canvas.add_block(ref)

        # Sum block (error = ref - meas)
        sum_block = SumBlock("sum_0", signs=["+", "-"])
        sum_block.position = QPointF(180, 150)
        self.canvas.add_block(sum_block)

        # PID controller
        pid = PIDBlock("pid_0", "PID", slot=0)
        pid.position = QPointF(300, 140)
        self.canvas.add_block(pid)

        # Motor service (plant/actuator)
        motor = MotorServiceBlock("motor_svc_0")
        motor.position = QPointF(450, 120)
        self.canvas.add_block(motor)

        # Feedback signal (measurement)
        feedback = SignalSourceBlock("feedback_0", "Encoder", signal_id=1)
        feedback.position = QPointF(300, 280)
        self.canvas.add_block(feedback)

        # Connections
        self.canvas.add_connection("ref_0", "out", "sum_0", "in0")
        self.canvas.add_connection("sum_0", "out", "pid_0", "ref")
        self.canvas.add_connection("pid_0", "out", "motor_svc_0", "speed_0")
        self.canvas.add_connection("feedback_0", "out", "sum_0", "in1")

        self.canvas.zoom_to_fit()
        self.diagram_changed.emit()

    def _load_servo_example(self) -> None:
        """Load a servo position control example."""
        self.canvas.clear()

        # Position setpoint
        ref = SignalSourceBlock("ref_0", "Position", signal_id=0)
        ref.position = QPointF(50, 150)
        self.canvas.add_block(ref)

        # Gain block (scale to servo range)
        gain = GainBlock("gain_0")
        gain.position = QPointF(180, 150)
        self.canvas.add_block(gain)

        # Saturation (limit to 0-180 degrees)
        sat = SaturationBlock("sat_0")
        sat.position = QPointF(300, 150)
        self.canvas.add_block(sat)

        # Servo service
        servo = ServoServiceBlock("servo_svc_0")
        servo.position = QPointF(450, 130)
        self.canvas.add_block(servo)

        # Connections
        self.canvas.add_connection("ref_0", "out", "gain_0", "in")
        self.canvas.add_connection("gain_0", "out", "sat_0", "in")
        self.canvas.add_connection("sat_0", "out", "servo_svc_0", "angle_0")

        self.canvas.zoom_to_fit()
        self.diagram_changed.emit()

    def _load_encoder_feedback_example(self) -> None:
        """Load motor with encoder feedback example."""
        self.canvas.clear()

        # Velocity setpoint
        ref = SignalSourceBlock("ref_0", "Vel Ref", signal_id=0)
        ref.position = QPointF(50, 150)
        self.canvas.add_block(ref)

        # Error summing junction
        sum_block = SumBlock("sum_0", signs=["+", "-"])
        sum_block.position = QPointF(180, 150)
        self.canvas.add_block(sum_block)

        # PID controller
        pid = PIDBlock("pid_0", "Velocity PID", slot=0)
        pid.position = QPointF(300, 140)
        self.canvas.add_block(pid)

        # Saturation (motor limits)
        sat = SaturationBlock("sat_0")
        sat.position = QPointF(430, 150)
        self.canvas.add_block(sat)

        # Motor service
        motor = MotorServiceBlock("motor_svc_0")
        motor.position = QPointF(560, 130)
        self.canvas.add_block(motor)

        # Low-pass filter on encoder feedback
        filt = FilterBlock("filter_0")
        filt.position = QPointF(300, 280)
        self.canvas.add_block(filt)

        # Encoder feedback
        encoder = SignalSourceBlock("encoder_0", "Encoder", signal_id=1)
        encoder.position = QPointF(450, 280)
        self.canvas.add_block(encoder)

        # Connections
        self.canvas.add_connection("ref_0", "out", "sum_0", "in0")
        self.canvas.add_connection("sum_0", "out", "pid_0", "ref")
        self.canvas.add_connection("pid_0", "out", "sat_0", "in")
        self.canvas.add_connection("sat_0", "out", "motor_svc_0", "speed_0")
        self.canvas.add_connection("encoder_0", "out", "filter_0", "in")
        self.canvas.add_connection("filter_0", "out", "sum_0", "in1")

        self.canvas.zoom_to_fit()
        self.diagram_changed.emit()

    def _load_cascaded_pid_example(self) -> None:
        """Load cascaded PID (position + velocity) example."""
        self.canvas.clear()

        # Position setpoint
        pos_ref = SignalSourceBlock("pos_ref", "Pos Ref", signal_id=0)
        pos_ref.position = QPointF(50, 100)
        self.canvas.add_block(pos_ref)

        # Position error
        pos_sum = SumBlock("pos_sum", signs=["+", "-"])
        pos_sum.position = QPointF(180, 100)
        self.canvas.add_block(pos_sum)

        # Position (outer) PID
        pos_pid = PIDBlock("pos_pid", "Position PID", slot=0)
        pos_pid.position = QPointF(300, 90)
        self.canvas.add_block(pos_pid)

        # Velocity error
        vel_sum = SumBlock("vel_sum", signs=["+", "-"])
        vel_sum.position = QPointF(430, 100)
        self.canvas.add_block(vel_sum)

        # Velocity (inner) PID
        vel_pid = PIDBlock("vel_pid", "Velocity PID", slot=1)
        vel_pid.position = QPointF(550, 90)
        self.canvas.add_block(vel_pid)

        # Motor output
        motor = MotorServiceBlock("motor_svc_0")
        motor.position = QPointF(700, 70)
        self.canvas.add_block(motor)

        # Position feedback
        pos_fb = SignalSourceBlock("pos_fb", "Position", signal_id=1)
        pos_fb.position = QPointF(180, 250)
        self.canvas.add_block(pos_fb)

        # Velocity feedback (derivative of position or direct encoder)
        vel_fb = SignalSourceBlock("vel_fb", "Velocity", signal_id=2)
        vel_fb.position = QPointF(430, 250)
        self.canvas.add_block(vel_fb)

        # Connections - outer loop
        self.canvas.add_connection("pos_ref", "out", "pos_sum", "in0")
        self.canvas.add_connection("pos_fb", "out", "pos_sum", "in1")
        self.canvas.add_connection("pos_sum", "out", "pos_pid", "ref")

        # Connections - inner loop
        self.canvas.add_connection("pos_pid", "out", "vel_sum", "in0")
        self.canvas.add_connection("vel_fb", "out", "vel_sum", "in1")
        self.canvas.add_connection("vel_sum", "out", "vel_pid", "ref")
        self.canvas.add_connection("vel_pid", "out", "motor_svc_0", "speed_0")

        self.canvas.zoom_to_fit()
        self.diagram_changed.emit()

    def create_basic_pid_loop(self) -> None:
        """Create a basic PID control loop as a starting point (legacy method)."""
        self._load_basic_pid_example()
