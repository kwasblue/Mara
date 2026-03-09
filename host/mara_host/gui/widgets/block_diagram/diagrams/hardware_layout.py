# mara_host/gui/widgets/block_diagram/diagrams/hardware_layout.py
"""Hardware layout diagram view."""

import uuid

from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QPushButton,
    QFrame,
    QMessageBox,
)

from ..core.canvas import DiagramCanvas
from ..core.models import DiagramState
from ..blocks.esp32 import ESP32Block
from ..blocks.motor import MotorBlock
from ..blocks.encoder import EncoderBlock
from ..blocks.servo import ServoBlock
from ..blocks.sensor import SensorBlock
from .palette import ComponentPalette


class HardwareLayoutDiagram(QWidget):
    """
    Hardware Layout diagram view.

    Shows ESP32 MCU with connected peripherals (motors, encoders, sensors).
    Supports drag-and-drop from component palette and wire connections.

    Signals:
        diagram_changed(): Emitted when diagram state changes
        block_configured(str, dict): Emitted when a block is configured
    """

    diagram_changed = Signal()
    block_configured = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pin_service = None
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

        title = QLabel("Hardware Layout")
        title.setStyleSheet("font-weight: 600; color: #FAFAFA;")
        toolbar_layout.addWidget(title)

        toolbar_layout.addStretch()

        # Toolbar buttons
        self.add_esp_btn = QPushButton("+ ESP32")
        self.add_esp_btn.setObjectName("secondary")
        self.add_esp_btn.clicked.connect(self._add_esp32)
        toolbar_layout.addWidget(self.add_esp_btn)

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
        self.palette = ComponentPalette(palette_type="hardware")
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
        self.canvas.diagram_changed.connect(self.diagram_changed.emit)
        self.canvas.block_configured.connect(self.block_configured.emit)
        self.canvas.block_double_clicked.connect(self._on_block_double_clicked)

    def set_pin_service(self, pin_service) -> None:
        """Set the pin service for auto pin assignment."""
        self._pin_service = pin_service

    def _add_esp32(self) -> None:
        """Add an ESP32 block to the canvas."""
        # Check if ESP32 already exists
        for block in self.canvas.get_blocks():
            if block.block_type == "esp32":
                QMessageBox.information(
                    self,
                    "ESP32 Already Exists",
                    "Only one ESP32 block can be added to the diagram.",
                )
                return

        block_id = f"esp32_{uuid.uuid4().hex[:6]}"
        block = ESP32Block(block_id, "ESP32")
        block.position = QPointF(200, 50)
        self.canvas.add_block(block)

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

        if component_type == "esp32":
            # Check if ESP32 already exists
            for b in self.canvas.get_blocks():
                if b.block_type == "esp32":
                    return
            block = ESP32Block(block_id)

        elif component_type == "motor":
            # Count existing motors
            motor_count = sum(1 for b in self.canvas.get_blocks() if b.block_type == "motor")
            block = MotorBlock(block_id, f"Motor {motor_count}", motor_count)

        elif component_type == "encoder":
            encoder_count = sum(1 for b in self.canvas.get_blocks() if b.block_type == "encoder")
            block = EncoderBlock(block_id, f"Encoder {encoder_count}", encoder_count)

        elif component_type == "servo":
            servo_count = sum(1 for b in self.canvas.get_blocks() if b.block_type == "servo")
            block = ServoBlock(block_id, f"Servo {servo_count}", servo_count)

        elif component_type.startswith("sensor_"):
            sensor_type = component_type.replace("sensor_", "")
            block = SensorBlock(block_id, sensor_type)

        if block:
            block.position = pos
            self.canvas.add_block(block)

            # Auto-suggest pins if pin service available
            if self._pin_service and hasattr(block, "get_suggested_pins"):
                self._suggest_pins_for_block(block)

    def _suggest_pins_for_block(self, block) -> None:
        """Get pin suggestions from PinService."""
        if not self._pin_service:
            return

        # Get ESP32 block for pin assignment
        esp32 = None
        for b in self.canvas.get_blocks():
            if b.block_type == "esp32":
                esp32 = b
                break

        if not esp32:
            return

        # Get recommendations based on block type
        if block.block_type == "motor":
            motor_id = str(block.config.properties.get("motor_id", 0))
            rec = self._pin_service.recommend_motor_pins(motor_id)
            # Could auto-create connections here

        elif block.block_type == "encoder":
            enc_id = str(block.config.properties.get("encoder_id", 0))
            rec = self._pin_service.recommend_encoder_pins(enc_id)

        elif block.block_type == "servo":
            servo_id = str(block.config.properties.get("servo_id", 0))
            rec = self._pin_service.recommend_servo_pins(servo_id)

    def _on_block_double_clicked(self, block_id: str) -> None:
        """Handle block double-click."""
        block = self.canvas.get_block(block_id)
        if block:
            dialog = block.get_config_dialog(self)
            if dialog and dialog.exec():
                if hasattr(dialog, "get_config"):
                    config = dialog.get_config()
                    block.apply_config(config)
                    self.block_configured.emit(block_id, config)
                    self.canvas.update()

    def get_state(self) -> DiagramState:
        """Get current diagram state."""
        state = self.canvas.get_state()
        state.diagram_type = "hardware"
        return state

    def load_state(self, state: DiagramState) -> None:
        """Load diagram state."""
        self.canvas.clear()
        # Would need block factory to recreate blocks from config
        # For now, just emit changed
        self.diagram_changed.emit()
