# mara_host/gui/panels/pinout/board_diagram.py
"""Visual ESP32 board diagram widget for interactive pin configuration."""

from typing import Optional, Dict
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QGroupBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QSize
from PySide6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QPainterPath,
    QLinearGradient,
)


# Pin status colors (matching pin_table.py)
PIN_COLORS = {
    "assigned": QColor("#22C55E"),     # Green
    "free_safe": QColor("#3B82F6"),    # Blue
    "free_boot": QColor("#EAB308"),    # Yellow
    "free_input": QColor("#A855F7"),   # Purple
    "flash": QColor("#EF4444"),        # Red (unusable)
    "conflict": QColor("#F97316"),     # Orange
    "selected": QColor("#06B6D4"),     # Cyan
    "hover": QColor("#8B5CF6"),        # Violet
    "default": QColor("#6B7280"),      # Gray
}


@dataclass
class PinPosition:
    """Position and info for a pin on the board."""
    gpio: int
    x: float
    y: float
    side: str  # 'left' or 'right'
    label: str  # Pin label on board (e.g., "D2", "3V3")


# ESP32-DevKitC V4 pinout (30-pin variant)
# Left side (top to bottom), Right side (top to bottom)
ESP32_DEVKIT_PINS = {
    # Left side (top to bottom)
    "left": [
        (None, "3V3"),   # 3.3V power
        (None, "GND"),   # Ground
        (15, "D15"),
        (2, "D2"),
        (4, "D4"),
        (16, "RX2"),
        (17, "TX2"),
        (5, "D5"),
        (18, "D18"),
        (19, "D19"),
        (21, "D21"),
        (None, "GND"),
        (22, "D22"),
        (23, "D23"),
        (None, "EN"),    # Enable
    ],
    # Right side (top to bottom)
    "right": [
        (None, "VIN"),   # 5V input
        (None, "GND"),
        (13, "D13"),
        (12, "D12"),
        (14, "D14"),
        (27, "D27"),
        (26, "D26"),
        (25, "D25"),
        (33, "D33"),
        (32, "D32"),
        (35, "D35"),
        (34, "D34"),
        (None, "VN"),    # VP/VN ADC
        (None, "VP"),
        (None, "GND"),
    ],
}

# ESP32-DevKitC V4 38-pin variant
ESP32_DEVKIT_38_PINS = {
    "left": [
        (None, "3V3"),
        (None, "EN"),
        (36, "VP"),
        (39, "VN"),
        (34, "D34"),
        (35, "D35"),
        (32, "D32"),
        (33, "D33"),
        (25, "D25"),
        (26, "D26"),
        (27, "D27"),
        (14, "D14"),
        (12, "D12"),
        (None, "GND"),
        (13, "D13"),
        (9, "SD2"),
        (10, "SD3"),
        (11, "CMD"),
        (None, "5V"),
    ],
    "right": [
        (None, "GND"),
        (23, "D23"),
        (22, "D22"),
        (1, "TX0"),
        (3, "RX0"),
        (21, "D21"),
        (None, "GND"),
        (19, "D19"),
        (18, "D18"),
        (5, "D5"),
        (17, "TX2"),
        (16, "RX2"),
        (4, "D4"),
        (0, "D0"),
        (2, "D2"),
        (15, "D15"),
        (8, "SD1"),
        (7, "SD0"),
        (6, "CLK"),
    ],
}


class ESP32BoardWidget(QWidget):
    """
    Interactive ESP32 board diagram widget.

    Signals:
        pin_selected(int): Emitted when a GPIO pin is clicked
        pin_hovered(int): Emitted when mouse hovers over a pin
    """

    pin_selected = Signal(int)
    pin_hovered = Signal(int)

    # Board dimensions (relative units)
    BOARD_WIDTH = 180
    BOARD_HEIGHT = 480  # Increased to fit 38-pin variant
    PIN_RADIUS = 8
    PIN_SPACING = 22
    PIN_MARGIN = 25
    CHIP_WIDTH = 80
    CHIP_HEIGHT = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pin_service = None
        self._pin_positions: Dict[int, QRectF] = {}
        self._selected_gpio: Optional[int] = None
        self._hovered_gpio: Optional[int] = None
        self._board_variant = "38-pin"  # or "30-pin"

        self.setMinimumSize(320, 580)  # Larger to fit all 38 pins
        self.setMouseTracking(True)

    def set_pin_service(self, pin_service) -> None:
        """Set the pin service for status info."""
        self._pin_service = pin_service
        self.update()

    def set_board_variant(self, variant: str) -> None:
        """Set board variant ('30-pin' or '38-pin')."""
        self._board_variant = variant
        self._calculate_pin_positions()
        self.update()

    def set_selected_pin(self, gpio: int) -> None:
        """Set the currently selected pin."""
        self._selected_gpio = gpio
        self.update()

    def sizeHint(self):
        """Return preferred size based on board variant."""
        # Calculate height needed for pins
        layout = self._get_pin_layout()
        num_pins = max(len(layout.get("left", [])), len(layout.get("right", [])))
        height = 60 + num_pins * self.PIN_SPACING + 40  # margins + pins + footer
        return QSize(320, max(580, height))

    def _get_pin_layout(self) -> Dict:
        """Get pin layout for current variant."""
        if self._board_variant == "38-pin":
            return ESP32_DEVKIT_38_PINS
        return ESP32_DEVKIT_PINS

    def _calculate_pin_positions(self) -> None:
        """Calculate pin positions based on widget size."""
        self._pin_positions.clear()

        layout = self._get_pin_layout()

        # Calculate scale
        w = self.width()
        h = self.height()
        scale_x = w / (self.BOARD_WIDTH + 80)
        scale_y = h / (self.BOARD_HEIGHT + 40)
        scale = min(scale_x, scale_y)

        # Board position (centered)
        board_w = self.BOARD_WIDTH * scale
        board_h = self.BOARD_HEIGHT * scale
        board_x = (w - board_w) / 2
        board_y = (h - board_h) / 2 + 20

        pin_radius = self.PIN_RADIUS * scale
        pin_spacing = self.PIN_SPACING * scale

        # Left side pins
        left_pins = layout.get("left", [])
        start_y = board_y + 30 * scale
        for i, (gpio, label) in enumerate(left_pins):
            if gpio is not None:
                x = board_x - pin_radius
                y = start_y + i * pin_spacing
                rect = QRectF(x - pin_radius, y - pin_radius,
                             pin_radius * 2, pin_radius * 2)
                self._pin_positions[gpio] = rect

        # Right side pins
        right_pins = layout.get("right", [])
        for i, (gpio, label) in enumerate(right_pins):
            if gpio is not None:
                x = board_x + board_w + pin_radius
                y = start_y + i * pin_spacing
                rect = QRectF(x - pin_radius, y - pin_radius,
                             pin_radius * 2, pin_radius * 2)
                self._pin_positions[gpio] = rect

    def _get_pin_color(self, gpio: int) -> QColor:
        """Get the color for a pin based on its status."""
        if gpio == self._selected_gpio:
            return PIN_COLORS["selected"]
        if gpio == self._hovered_gpio:
            return PIN_COLORS["hover"]

        if not self._pin_service:
            return PIN_COLORS["default"]

        try:
            # Check if assigned
            assignments = self._pin_service.get_assignments()
            for name, g in assignments.items():
                if g == gpio:
                    return PIN_COLORS["assigned"]

            # Check for conflicts
            conflicts = self._pin_service.detect_conflicts()
            conflict_gpios = {c.gpio for c in conflicts}
            if gpio in conflict_gpios:
                return PIN_COLORS["conflict"]

            # Check pin type
            if self._pin_service.is_flash_pin(gpio):
                return PIN_COLORS["flash"]
            if self._pin_service.is_safe_pin(gpio):
                return PIN_COLORS["free_safe"]
            if self._pin_service.is_boot_pin(gpio):
                return PIN_COLORS["free_boot"]
            if self._pin_service.is_input_only(gpio):
                return PIN_COLORS["free_input"]

        except Exception:
            pass

        return PIN_COLORS["default"]

    def _get_pin_name(self, gpio: int) -> Optional[str]:
        """Get assigned name for a pin."""
        if not self._pin_service:
            return None
        try:
            assignments = self._pin_service.get_assignments()
            for name, g in assignments.items():
                if g == gpio:
                    return name
        except Exception:
            pass
        return None

    def paintEvent(self, event) -> None:
        """Paint the board diagram."""
        self._calculate_pin_positions()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Calculate scale
        scale_x = w / (self.BOARD_WIDTH + 80)
        scale_y = h / (self.BOARD_HEIGHT + 40)
        scale = min(scale_x, scale_y)

        # Board dimensions
        board_w = self.BOARD_WIDTH * scale
        board_h = self.BOARD_HEIGHT * scale
        board_x = (w - board_w) / 2
        board_y = (h - board_h) / 2 + 20

        # Draw board background
        self._draw_board(painter, board_x, board_y, board_w, board_h, scale)

        # Draw pins
        self._draw_pins(painter, board_x, board_y, board_w, board_h, scale)

        # Draw title
        painter.setPen(QPen(QColor("#E5E7EB")))
        title_font = QFont("Arial", int(12 * scale))
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(QRectF(0, 5, w, 25), Qt.AlignCenter,
                        f"ESP32-DevKitC ({self._board_variant})")

    def _draw_board(self, painter: QPainter, x: float, y: float,
                    w: float, h: float, scale: float) -> None:
        """Draw the PCB board."""
        # Board outline with rounded corners
        board_color = QColor("#1E3A5F")
        painter.setPen(QPen(QColor("#2563EB"), 2))
        painter.setBrush(QBrush(board_color))

        path = QPainterPath()
        radius = 8 * scale
        path.addRoundedRect(QRectF(x, y, w, h), radius, radius)
        painter.drawPath(path)

        # USB connector at bottom
        usb_w = 30 * scale
        usb_h = 15 * scale
        usb_x = x + (w - usb_w) / 2
        usb_y = y + h - usb_h / 2

        painter.setPen(QPen(QColor("#9CA3AF"), 1))
        painter.setBrush(QBrush(QColor("#4B5563")))
        painter.drawRect(QRectF(usb_x, usb_y, usb_w, usb_h))

        # ESP32 chip in center
        chip_w = self.CHIP_WIDTH * scale
        chip_h = self.CHIP_HEIGHT * scale
        chip_x = x + (w - chip_w) / 2
        chip_y = y + (h - chip_h) / 2 - 20 * scale

        # Chip with gradient
        gradient = QLinearGradient(chip_x, chip_y, chip_x, chip_y + chip_h)
        gradient.setColorAt(0, QColor("#374151"))
        gradient.setColorAt(1, QColor("#1F2937"))

        painter.setPen(QPen(QColor("#6B7280"), 1))
        painter.setBrush(QBrush(gradient))
        painter.drawRect(QRectF(chip_x, chip_y, chip_w, chip_h))

        # Chip label
        painter.setPen(QPen(QColor("#9CA3AF")))
        label_font = QFont("Arial", int(8 * scale))
        painter.setFont(label_font)
        painter.drawText(QRectF(chip_x, chip_y, chip_w, chip_h),
                        Qt.AlignCenter, "ESP32\nWROOM")

        # Orientation marker (pin 1 dot)
        dot_radius = 4 * scale
        painter.setBrush(QBrush(QColor("#EF4444")))
        painter.drawEllipse(QPointF(chip_x + dot_radius * 2, chip_y + dot_radius * 2),
                           dot_radius, dot_radius)

    def _draw_pins(self, painter: QPainter, board_x: float, board_y: float,
                   board_w: float, board_h: float, scale: float) -> None:
        """Draw all pins with labels."""
        layout = self._get_pin_layout()

        pin_radius = self.PIN_RADIUS * scale
        pin_spacing = self.PIN_SPACING * scale

        label_font = QFont("Consolas", int(7 * scale))
        small_font = QFont("Consolas", int(6 * scale))
        painter.setFont(label_font)

        start_y = board_y + 30 * scale

        # Left side pins
        for i, (gpio, label) in enumerate(layout.get("left", [])):
            x = board_x - pin_radius
            y = start_y + i * pin_spacing

            # Pin hole on board
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.setBrush(QBrush(QColor("#0F172A")))
            painter.drawEllipse(QPointF(board_x + pin_radius, y),
                               pin_radius * 0.6, pin_radius * 0.6)

            if gpio is not None:
                # GPIO pin (colored circle)
                color = self._get_pin_color(gpio)
                painter.setPen(QPen(color.darker(120), 1))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(QPointF(x, y), pin_radius, pin_radius)

                # GPIO number on pin
                painter.setPen(QPen(QColor("#FFFFFF")))
                painter.setFont(small_font)
                painter.drawText(QRectF(x - pin_radius, y - pin_radius,
                                       pin_radius * 2, pin_radius * 2),
                                Qt.AlignCenter, str(gpio))

                # Label to the left
                painter.setFont(label_font)
                painter.setPen(QPen(QColor("#9CA3AF")))
                assigned_name = self._get_pin_name(gpio)
                if assigned_name:
                    painter.setPen(QPen(PIN_COLORS["assigned"]))
                    display_label = assigned_name[:8]
                else:
                    display_label = label
                painter.drawText(QRectF(x - 80 * scale, y - 8 * scale,
                                       70 * scale, 16 * scale),
                                Qt.AlignRight | Qt.AlignVCenter, display_label)
            else:
                # Power/GND pin (square)
                painter.setPen(QPen(QColor("#6B7280"), 1))
                if "GND" in label:
                    painter.setBrush(QBrush(QColor("#1F2937")))
                elif "3V" in label or "5V" in label or "VIN" in label:
                    painter.setBrush(QBrush(QColor("#DC2626")))
                else:
                    painter.setBrush(QBrush(QColor("#4B5563")))
                painter.drawRect(QRectF(x - pin_radius * 0.8, y - pin_radius * 0.8,
                                       pin_radius * 1.6, pin_radius * 1.6))

                # Label
                painter.setPen(QPen(QColor("#6B7280")))
                painter.setFont(label_font)
                painter.drawText(QRectF(x - 80 * scale, y - 8 * scale,
                                       70 * scale, 16 * scale),
                                Qt.AlignRight | Qt.AlignVCenter, label)

        # Right side pins
        for i, (gpio, label) in enumerate(layout.get("right", [])):
            x = board_x + board_w + pin_radius
            y = start_y + i * pin_spacing

            # Pin hole on board
            painter.setPen(QPen(QColor("#0F172A"), 1))
            painter.setBrush(QBrush(QColor("#0F172A")))
            painter.drawEllipse(QPointF(board_x + board_w - pin_radius, y),
                               pin_radius * 0.6, pin_radius * 0.6)

            if gpio is not None:
                # GPIO pin
                color = self._get_pin_color(gpio)
                painter.setPen(QPen(color.darker(120), 1))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(QPointF(x, y), pin_radius, pin_radius)

                # GPIO number
                painter.setPen(QPen(QColor("#FFFFFF")))
                painter.setFont(small_font)
                painter.drawText(QRectF(x - pin_radius, y - pin_radius,
                                       pin_radius * 2, pin_radius * 2),
                                Qt.AlignCenter, str(gpio))

                # Label to the right
                painter.setFont(label_font)
                painter.setPen(QPen(QColor("#9CA3AF")))
                assigned_name = self._get_pin_name(gpio)
                if assigned_name:
                    painter.setPen(QPen(PIN_COLORS["assigned"]))
                    display_label = assigned_name[:8]
                else:
                    display_label = label
                painter.drawText(QRectF(x + 12 * scale, y - 8 * scale,
                                       70 * scale, 16 * scale),
                                Qt.AlignLeft | Qt.AlignVCenter, display_label)
            else:
                # Power/GND pin
                painter.setPen(QPen(QColor("#6B7280"), 1))
                if "GND" in label:
                    painter.setBrush(QBrush(QColor("#1F2937")))
                elif "3V" in label or "5V" in label or "VIN" in label:
                    painter.setBrush(QBrush(QColor("#DC2626")))
                else:
                    painter.setBrush(QBrush(QColor("#4B5563")))
                painter.drawRect(QRectF(x - pin_radius * 0.8, y - pin_radius * 0.8,
                                       pin_radius * 1.6, pin_radius * 1.6))

                painter.setPen(QPen(QColor("#6B7280")))
                painter.setFont(label_font)
                painter.drawText(QRectF(x + 12 * scale, y - 8 * scale,
                                       70 * scale, 16 * scale),
                                Qt.AlignLeft | Qt.AlignVCenter, label)

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse hover."""
        pos = event.position()
        new_hover = None

        for gpio, rect in self._pin_positions.items():
            if rect.contains(pos):
                new_hover = gpio
                break

        if new_hover != self._hovered_gpio:
            self._hovered_gpio = new_hover
            if new_hover is not None:
                self.pin_hovered.emit(new_hover)
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            self.update()

    def mousePressEvent(self, event) -> None:
        """Handle pin click."""
        if event.button() != Qt.LeftButton:
            return

        pos = event.position()

        for gpio, rect in self._pin_positions.items():
            if rect.contains(pos):
                self._selected_gpio = gpio
                self.pin_selected.emit(gpio)
                self.update()
                return

    def resizeEvent(self, event) -> None:
        """Handle resize."""
        self._calculate_pin_positions()
        super().resizeEvent(event)


class BoardDiagramWidget(QGroupBox):
    """
    Container widget for ESP32 board diagram with controls.

    Signals:
        pin_selected(int): Emitted when a GPIO pin is selected
    """

    pin_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__("ESP32 Board Diagram", parent)
        self._pin_service = None
        self._setup_ui()

    def set_pin_service(self, pin_service) -> None:
        """Set the pin service instance."""
        self._pin_service = pin_service
        self.board_widget.set_pin_service(pin_service)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Board variant selector
        variant_layout = QHBoxLayout()
        variant_layout.addWidget(QLabel("Board:"))

        self.variant_combo = QComboBox()
        self.variant_combo.addItems(["38-pin DevKitC", "30-pin DevKitC"])
        self.variant_combo.currentIndexChanged.connect(self._on_variant_changed)
        variant_layout.addWidget(self.variant_combo)

        variant_layout.addStretch()

        # Legend
        legend = QLabel(
            '<span style="color: #22C55E;">Assigned</span> | '
            '<span style="color: #3B82F6;">Safe</span> | '
            '<span style="color: #EAB308;">Boot</span> | '
            '<span style="color: #EF4444;">Flash</span> | '
            '<span style="color: #06B6D4;">Selected</span>'
        )
        legend.setStyleSheet("font-size: 10px;")
        variant_layout.addWidget(legend)

        layout.addLayout(variant_layout)

        # Board widget in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.board_widget = ESP32BoardWidget()
        self.board_widget.pin_selected.connect(self._on_pin_selected)
        self.board_widget.pin_hovered.connect(self._on_pin_hovered)
        scroll.setWidget(self.board_widget)

        layout.addWidget(scroll, 1)

        # Hover info
        self.hover_label = QLabel("Click a pin to select it")
        self.hover_label.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        layout.addWidget(self.hover_label)

    def _on_variant_changed(self, index: int) -> None:
        """Handle board variant change."""
        variant = "38-pin" if index == 0 else "30-pin"
        self.board_widget.set_board_variant(variant)

    def _on_pin_selected(self, gpio: int) -> None:
        """Handle pin selection."""
        self.pin_selected.emit(gpio)

    def _on_pin_hovered(self, gpio: int) -> None:
        """Handle pin hover."""
        if not self._pin_service:
            self.hover_label.setText(f"GPIO {gpio}")
            return

        try:
            info = self._pin_service.get_pin_info(gpio)
            caps = self._pin_service.capability_string(gpio)

            # Get assignment
            assignments = self._pin_service.get_assignments()
            assigned_name = None
            for name, g in assignments.items():
                if g == gpio:
                    assigned_name = name
                    break

            if assigned_name:
                text = f"GPIO {gpio}: {assigned_name} [{caps}]"
            else:
                text = f"GPIO {gpio}: {caps}"

            if self._pin_service.is_flash_pin(gpio):
                text += " - DO NOT USE (Flash)"
            elif self._pin_service.is_boot_pin(gpio):
                text += " - Boot pin (use with caution)"

            self.hover_label.setText(text)

        except Exception:
            self.hover_label.setText(f"GPIO {gpio}")

    def refresh(self) -> None:
        """Refresh the board display."""
        self.board_widget.update()

    def set_selected_pin(self, gpio: int) -> None:
        """Set the selected pin."""
        self.board_widget.set_selected_pin(gpio)
