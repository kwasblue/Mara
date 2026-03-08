# mara_host/gui/widgets/block_diagram/diagrams/palette.py
"""Component palette sidebar for dragging blocks onto the canvas."""


from PySide6.QtCore import Qt, Signal, QMimeData, QPoint
from PySide6.QtGui import QDrag, QPainter, QPen, QBrush, QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
)

from ..blocks.sensor import SENSOR_TYPES


def _build_hardware_components() -> list[dict]:
    """Build hardware component list, auto-including sensors from SENSOR_TYPES."""
    # Core hardware (not sensors)
    components = [
        {
            "type": "esp32",
            "label": "ESP32",
            "description": "ESP32 MCU with GPIO pins",
            "color": "#06B6D4",
        },
        {
            "type": "motor",
            "label": "DC Motor",
            "description": "DC motor with driver",
            "color": "#EF4444",
        },
        {
            "type": "encoder",
            "label": "Encoder",
            "description": "Quadrature encoder",
            "color": "#8B5CF6",
        },
        {
            "type": "servo",
            "label": "Servo",
            "description": "Servo motor",
            "color": "#F59E0B",
        },
    ]

    # Auto-add sensors from SENSOR_TYPES
    for sensor_key, sensor_config in SENSOR_TYPES.items():
        components.append({
            "type": f"sensor_{sensor_key}",
            "label": sensor_config["label"],
            "description": f"{sensor_config['label']} sensor ({sensor_config['interface'].upper()})",
            "color": sensor_config["color"],
        })

    return components


# Component definitions for palette (sensors auto-generated from SENSOR_TYPES)
HARDWARE_COMPONENTS = _build_hardware_components()

CONTROL_COMPONENTS = [
    {
        "type": "pid",
        "label": "PID",
        "description": "PID controller",
        "color": "#3B82F6",
    },
    {
        "type": "observer",
        "label": "Observer",
        "description": "State observer",
        "color": "#22C55E",
    },
    {
        "type": "signal_source",
        "label": "Signal",
        "description": "Signal source",
        "color": "#3B82F6",
    },
    {
        "type": "signal_sink",
        "label": "Output",
        "description": "Signal sink/output",
        "color": "#F59E0B",
    },
    {
        "type": "sum",
        "label": "Sum",
        "description": "Summing junction",
        "color": "#71717A",
    },
    {
        "type": "gain",
        "label": "Gain",
        "description": "Scalar gain",
        "color": "#8B5CF6",
    },
]

SERVICE_COMPONENTS = [
    {
        "type": "motor_service",
        "label": "MotorService",
        "description": "Motor control service",
        "color": "#EF4444",
    },
    {
        "type": "servo_service",
        "label": "ServoService",
        "description": "Servo control service",
        "color": "#F59E0B",
    },
    {
        "type": "gpio_service",
        "label": "GPIOService",
        "description": "GPIO control service",
        "color": "#06B6D4",
    },
]


class ComponentItem(QFrame):
    """
    Draggable component item in the palette.
    """

    drag_started = Signal(str)  # component_type

    def __init__(
        self,
        component_type: str,
        label: str,
        description: str,
        color: str,
        parent=None,
    ):
        super().__init__(parent)
        self.component_type = component_type
        self.color = QColor(color)
        self._setup_ui(label, description)

    def _setup_ui(self, label: str, description: str) -> None:
        self.setFixedHeight(50)
        self.setCursor(Qt.OpenHandCursor)
        self.setStyleSheet("""
            ComponentItem {
                background-color: #1F1F23;
                border-radius: 6px;
                margin: 2px 4px;
            }
            ComponentItem:hover {
                background-color: #27272A;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Color indicator
        color_frame = QFrame()
        color_frame.setFixedSize(6, 30)
        color_frame.setStyleSheet(f"background-color: {self.color.name()}; border-radius: 3px;")
        layout.addWidget(color_frame)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        name_label = QLabel(label)
        name_label.setStyleSheet("font-weight: 500; color: #FAFAFA; font-size: 12px;")
        text_layout.addWidget(name_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #71717A; font-size: 10px;")
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
            self._drag_start_pos = event.position()

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return

        # Only start drag after minimum distance
        if not hasattr(self, '_drag_start_pos'):
            return

        distance = (event.position() - self._drag_start_pos).manhattanLength()
        if distance < 10:
            return

        # Start drag
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.component_type)
        drag.setMimeData(mime_data)

        # Create drag pixmap
        pixmap = QPixmap(80, 40)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(self.color, 2))
        painter.setBrush(QBrush(QColor("#1F1F23")))
        painter.drawRoundedRect(2, 2, 76, 36, 6, 6)
        painter.setPen(QPen(self.color))
        painter.setFont(QFont("Helvetica Neue", 9))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, self.component_type[:8])
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(40, 20))

        self.drag_started.emit(self.component_type)
        drag.exec(Qt.CopyAction)


class ComponentPalette(QWidget):
    """
    Sidebar palette of components that can be dragged onto the canvas.

    Signals:
        component_drag_started(str): Emitted when drag begins
    """

    component_drag_started = Signal(str)

    def __init__(self, palette_type: str = "hardware", parent=None):
        """
        Initialize palette.

        Args:
            palette_type: "hardware", "control", or "all"
            parent: Parent widget
        """
        super().__init__(parent)
        self._palette_type = palette_type
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title
        title = QLabel("Components")
        title.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #A1A1AA;
            padding: 12px 16px 8px;
        """)
        layout.addWidget(title)

        # Scroll area for components
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(4, 0, 4, 8)
        scroll_layout.setSpacing(4)

        # Add component groups based on palette type
        if self._palette_type in ("hardware", "all"):
            self._add_component_group(scroll_layout, "Hardware", HARDWARE_COMPONENTS)

        if self._palette_type in ("control", "all"):
            self._add_component_group(scroll_layout, "Control", CONTROL_COMPONENTS)

        if self._palette_type == "all":
            self._add_component_group(scroll_layout, "Services", SERVICE_COMPONENTS)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Set background
        self.setStyleSheet("background-color: #18181B;")
        self.setMinimumWidth(180)
        self.setMaximumWidth(220)

    def _add_component_group(
        self,
        layout: QVBoxLayout,
        title: str,
        components: list[dict],
    ) -> None:
        """Add a group of components to the palette."""
        # Group header
        header = QLabel(title)
        header.setStyleSheet("""
            color: #52525B;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 12px 12px 4px;
        """)
        layout.addWidget(header)

        # Component items
        for comp in components:
            item = ComponentItem(
                component_type=comp["type"],
                label=comp["label"],
                description=comp["description"],
                color=comp["color"],
            )
            item.drag_started.connect(self.component_drag_started.emit)
            layout.addWidget(item)

    def set_palette_type(self, palette_type: str) -> None:
        """Change the palette type and rebuild."""
        if palette_type != self._palette_type:
            self._palette_type = palette_type
            # Clear and rebuild
            while self.layout().count():
                child = self.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self._setup_ui()
