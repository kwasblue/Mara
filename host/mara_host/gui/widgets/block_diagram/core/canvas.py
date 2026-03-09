# mara_host/gui/widgets/block_diagram/core/canvas.py
"""Main diagram canvas widget."""

import uuid
from typing import Optional

from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QWheelEvent, QMouseEvent
from PySide6.QtWidgets import QWidget, QMenu

from .models import (
    DiagramState,
    ConnectionConfig,
    PortKind,
    can_connect,
)
from .grid import Grid
from .block import BlockBase
from .port import Port
from .connection import Connection, paint_preview_connection


class DiagramCanvas(QWidget):
    """
    Main drawing surface for block diagrams.

    Features:
    - Grid rendering with snap-to-grid
    - Block selection, dragging, and configuration
    - Connection drawing with bezier curves
    - Pan and zoom support
    - Hit detection for blocks, ports, and connections

    Signals:
        block_selected(str): Emitted when a block is selected
        block_double_clicked(str): Emitted when a block is double-clicked
        block_configured(str, dict): Emitted when block config changes
        connection_created(str, str, str, str): from_block, from_port, to_block, to_port
        connection_deleted(str): connection_id
        diagram_changed(): Emitted when diagram state changes
    """

    block_selected = Signal(str)  # block_id
    block_double_clicked = Signal(str)  # block_id
    block_configured = Signal(str, dict)  # block_id, config
    connection_created = Signal(str, str, str, str)  # from_block, from_port, to_block, to_port
    connection_deleted = Signal(str)  # connection_id
    diagram_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Data
        self._blocks: dict[str, BlockBase] = {}
        self._connections: dict[str, Connection] = {}

        # Grid
        self._grid = Grid(grid_size=20, major_interval=5)

        # View transform
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._scale = 1.0
        self._min_scale = 0.25
        self._max_scale = 4.0

        # Interaction state
        self._selected_block_id: Optional[str] = None
        self._selected_connection_id: Optional[str] = None
        self._hovered_block_id: Optional[str] = None
        self._hovered_port: Optional[Port] = None
        self._hovered_connection_id: Optional[str] = None

        # Dragging
        self._drag_mode: Optional[str] = None  # "block", "pan", "connect"
        self._drag_start: Optional[QPointF] = None
        self._drag_offset: Optional[QPointF] = None

        # Connection drawing
        self._connect_from_port: Optional[Port] = None
        self._connect_preview_end: Optional[QPointF] = None
        self._connect_target_port: Optional[Port] = None  # Port under cursor during drag
        self._connect_valid: Optional[bool] = None  # Validity: None=no target, True=valid, False=invalid

        # Drop preview (for palette drag-and-drop)
        self._drop_preview_pos: Optional[QPointF] = None

        # Widget setup
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # Background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#111113"))
        self.setPalette(palette)

    # --- Public API ---

    def add_block(self, block: BlockBase) -> None:
        """
        Add a block to the diagram.

        Args:
            block: Block instance to add
        """
        self._blocks[block.block_id] = block
        self.diagram_changed.emit()
        self.update()

    def remove_block(self, block_id: str) -> None:
        """
        Remove a block and its connections.

        Args:
            block_id: ID of block to remove
        """
        if block_id not in self._blocks:
            return

        # Remove connections to/from this block
        to_remove = [
            conn_id
            for conn_id, conn in self._connections.items()
            if conn.from_port.parent_block_id == block_id
            or conn.to_port.parent_block_id == block_id
        ]
        for conn_id in to_remove:
            del self._connections[conn_id]
            self.connection_deleted.emit(conn_id)

        # Remove block
        del self._blocks[block_id]

        if self._selected_block_id == block_id:
            self._selected_block_id = None

        self.diagram_changed.emit()
        self.update()

    def get_block(self, block_id: str) -> Optional[BlockBase]:
        """Get block by ID."""
        return self._blocks.get(block_id)

    def get_blocks(self) -> list[BlockBase]:
        """Get all blocks."""
        return list(self._blocks.values())

    def add_connection(
        self,
        from_block_id: str,
        from_port_id: str,
        to_block_id: str,
        to_port_id: str,
        connection_id: Optional[str] = None,
        signal_id: Optional[int] = None,
        label: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add a connection between ports.

        Args:
            from_block_id: Source block ID
            from_port_id: Source port ID (local to block)
            to_block_id: Destination block ID
            to_port_id: Destination port ID (local to block)
            connection_id: Optional explicit ID
            signal_id: Optional signal bus ID
            label: Optional label

        Returns:
            Connection ID if created, None if invalid
        """
        from_block = self._blocks.get(from_block_id)
        to_block = self._blocks.get(to_block_id)

        if not from_block or not to_block:
            return None

        from_port = from_block.get_port(from_port_id)
        to_port = to_block.get_port(to_port_id)

        if not from_port or not to_port:
            return None

        # Validate connection
        if from_port.kind != PortKind.OUTPUT or to_port.kind != PortKind.INPUT:
            return None

        if not can_connect(from_port.port_type, to_port.port_type):
            return None

        # Create connection
        conn_id = connection_id or f"conn_{uuid.uuid4().hex[:8]}"
        config = ConnectionConfig(
            connection_id=conn_id,
            from_block=from_block_id,
            from_port=from_port_id,
            to_block=to_block_id,
            to_port=to_port_id,
            signal_id=signal_id,
            label=label,
        )

        connection = Connection(config, from_port, to_port)
        self._connections[conn_id] = connection

        # Update port states
        from_port.set_connected(True)
        to_port.set_connected(True)

        self.connection_created.emit(from_block_id, from_port_id, to_block_id, to_port_id)
        self.diagram_changed.emit()
        self.update()

        return conn_id

    def remove_connection(self, connection_id: str) -> None:
        """Remove a connection."""
        if connection_id not in self._connections:
            return

        conn = self._connections[connection_id]

        # Update port states (check if still connected via other connections)
        self._update_port_connected_state(conn.from_port)
        self._update_port_connected_state(conn.to_port)

        del self._connections[connection_id]

        if self._selected_connection_id == connection_id:
            self._selected_connection_id = None

        self.connection_deleted.emit(connection_id)
        self.diagram_changed.emit()
        self.update()

    def _update_port_connected_state(self, port: Port) -> None:
        """Update port connected state based on remaining connections."""
        for conn in self._connections.values():
            if conn.from_port is port or conn.to_port is port:
                return  # Still connected
        port.set_connected(False)

    def clear(self) -> None:
        """Clear all blocks and connections."""
        self._blocks.clear()
        self._connections.clear()
        self._selected_block_id = None
        self._selected_connection_id = None
        self.diagram_changed.emit()
        self.update()

    def get_state(self) -> DiagramState:
        """Get current diagram state for saving."""
        return DiagramState(
            diagram_type="generic",
            blocks=[block.config for block in self._blocks.values()],
            connections=[conn.config for conn in self._connections.values()],
        )

    def select_block(self, block_id: Optional[str]) -> None:
        """Select a block (or deselect if None)."""
        # Deselect previous
        if self._selected_block_id:
            block = self._blocks.get(self._selected_block_id)
            if block:
                block.set_selected(False)

        self._selected_block_id = block_id
        self._selected_connection_id = None

        if block_id:
            block = self._blocks.get(block_id)
            if block:
                block.set_selected(True)
            self.block_selected.emit(block_id)

        self.update()

    def set_grid_enabled(self, enabled: bool) -> None:
        """Enable or disable grid snap."""
        self._grid.enabled = enabled
        self.update()

    def zoom_to_fit(self) -> None:
        """Zoom to fit all blocks in view."""
        if not self._blocks:
            return

        # Calculate bounding box
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for block in self._blocks.values():
            rect = block.rect
            min_x = min(min_x, rect.left())
            min_y = min(min_y, rect.top())
            max_x = max(max_x, rect.right())
            max_y = max(max_y, rect.bottom())

        if min_x == float("inf"):
            return

        # Add margin
        margin = 50
        min_x -= margin
        min_y -= margin
        max_x += margin
        max_y += margin

        content_w = max_x - min_x
        content_h = max_y - min_y

        # Calculate scale to fit
        scale_x = self.width() / content_w
        scale_y = self.height() / content_h
        self._scale = min(scale_x, scale_y, self._max_scale)
        self._scale = max(self._scale, self._min_scale)

        # Center content
        self._offset_x = -min_x * self._scale + (self.width() - content_w * self._scale) / 2
        self._offset_y = -min_y * self._scale + (self.height() - content_h * self._scale) / 2

        self.update()

    # --- Coordinate Transformations ---

    def canvas_to_scene(self, canvas_point: QPointF) -> QPointF:
        """Convert canvas (widget) coordinates to scene coordinates."""
        return QPointF(
            (canvas_point.x() - self._offset_x) / self._scale,
            (canvas_point.y() - self._offset_y) / self._scale,
        )

    def scene_to_canvas(self, scene_point: QPointF) -> QPointF:
        """Convert scene coordinates to canvas (widget) coordinates."""
        return QPointF(
            scene_point.x() * self._scale + self._offset_x,
            scene_point.y() * self._scale + self._offset_y,
        )

    # --- Event Handlers ---

    def paintEvent(self, event) -> None:
        """Paint the diagram."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw grid
        self._grid.paint(
            painter,
            self.width(),
            self.height(),
            self._offset_x,
            self._offset_y,
            self._scale,
        )

        # Apply view transform
        painter.translate(self._offset_x, self._offset_y)
        painter.scale(self._scale, self._scale)

        # Draw connections (behind blocks)
        for connection in self._connections.values():
            connection.paint(painter)

        # Draw connection preview
        if self._connect_from_port and self._connect_preview_end:
            paint_preview_connection(
                painter,
                self._connect_from_port.position,
                self._connect_preview_end,
                self._connect_from_port.port_type,
                self._connect_valid,
            )

        # Draw blocks
        for block in self._blocks.values():
            block.paint(painter)

        # Draw drop preview (dashed rectangle showing where block will be placed)
        if self._drop_preview_pos:
            from PySide6.QtGui import QPen, QBrush
            preview_rect_size = 100  # Approximate block size
            pen = QPen(QColor("#3B82F6"), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(59, 130, 246, 30)))  # Semi-transparent blue
            painter.drawRoundedRect(
                int(self._drop_preview_pos.x()),
                int(self._drop_preview_pos.y()),
                preview_rect_size,
                60,
                8,
                8,
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            scene_pos = self.canvas_to_scene(event.position())

            # Check for port click
            port = self._find_port_at(scene_pos)
            if port:
                if port.is_output:
                    # Output port - start connection drag
                    self._drag_mode = "connect"
                    self._connect_from_port = port
                    self._connect_preview_end = scene_pos
                    return
                else:
                    # Input port - check if block handles port click (e.g., ESP32 pin info)
                    block = self._blocks.get(port.parent_block_id)
                    if block and hasattr(block, 'handle_port_click'):
                        global_pos = self.mapToGlobal(event.position().toPoint())
                        if block.handle_port_click(port, global_pos):
                            return

            # Check for block click
            block = self._find_block_at(scene_pos)
            if block:
                self.select_block(block.block_id)
                self._drag_mode = "block"
                self._drag_start = scene_pos
                self._drag_offset = QPointF(
                    scene_pos.x() - block.position.x(),
                    scene_pos.y() - block.position.y(),
                )
                block.set_dragging(True)
                return

            # Check for connection click
            conn = self._find_connection_at(scene_pos)
            if conn:
                self._selected_connection_id = conn.connection_id
                self._selected_block_id = None
                for block in self._blocks.values():
                    block.set_selected(False)
                conn.set_selected(True)
                self.update()
                return

            # Click on empty space - deselect
            self.select_block(None)
            self._selected_connection_id = None
            for conn in self._connections.values():
                conn.set_selected(False)
            self.update()

        elif event.button() == Qt.MiddleButton:
            # Start panning
            self._drag_mode = "pan"
            self._drag_start = event.position()

        elif event.button() == Qt.RightButton:
            # Check if right-clicking on a port (show pin info for output ports)
            scene_pos = self.canvas_to_scene(event.position())
            port = self._find_port_at(scene_pos)
            if port:
                block = self._blocks.get(port.parent_block_id)
                if block and hasattr(block, 'handle_port_click'):
                    global_pos = self.mapToGlobal(event.position().toPoint())
                    if block.handle_port_click(port, global_pos):
                        return

            # Context menu
            self._show_context_menu(event.position())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move."""
        scene_pos = self.canvas_to_scene(event.position())

        if self._drag_mode == "block" and self._selected_block_id:
            # Drag block
            block = self._blocks.get(self._selected_block_id)
            if block:
                new_pos = QPointF(
                    scene_pos.x() - self._drag_offset.x(),
                    scene_pos.y() - self._drag_offset.y(),
                )
                new_pos = self._grid.snap(new_pos)
                block.position = new_pos
                self.update()

        elif self._drag_mode == "pan":
            # Pan view
            delta = event.position() - self._drag_start
            self._offset_x += delta.x()
            self._offset_y += delta.y()
            self._drag_start = event.position()
            self.update()

        elif self._drag_mode == "connect":
            # Update connection preview
            self._connect_preview_end = scene_pos

            # Check for valid target port under cursor
            target_port = self._find_port_at(scene_pos)
            self._update_connect_target(target_port)
            self.update()

        else:
            # Hover detection
            self._update_hover(scene_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            if self._drag_mode == "block" and self._selected_block_id:
                block = self._blocks.get(self._selected_block_id)
                if block:
                    block.set_dragging(False)
                self.diagram_changed.emit()

            elif self._drag_mode == "connect" and self._connect_from_port:
                # Try to complete connection
                scene_pos = self.canvas_to_scene(event.position())
                target_port = self._find_port_at(scene_pos)

                if (
                    target_port
                    and target_port.is_input
                    and target_port.parent_block_id != self._connect_from_port.parent_block_id
                ):
                    # Valid connection target
                    self.add_connection(
                        self._connect_from_port.parent_block_id,
                        self._connect_from_port.config.port_id,
                        target_port.parent_block_id,
                        target_port.config.port_id,
                    )

                # Clear connection drawing state
                if self._connect_target_port:
                    self._connect_target_port.set_hovered(False)
                    self._connect_target_port.set_connect_valid(None)
                self._connect_from_port = None
                self._connect_preview_end = None
                self._connect_target_port = None
                self._connect_valid = None
                self.setCursor(Qt.ArrowCursor)
                self.update()

        self._drag_mode = None
        self._drag_start = None
        self._drag_offset = None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double-click (open config dialog)."""
        if event.button() == Qt.LeftButton:
            scene_pos = self.canvas_to_scene(event.position())
            block = self._find_block_at(scene_pos)
            if block:
                self.block_double_clicked.emit(block.block_id)
                self._open_block_config(block)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle zoom with scroll wheel."""
        # Get position before zoom
        pos = event.position()
        scene_pos_before = self.canvas_to_scene(pos)

        # Calculate zoom factor
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9

        new_scale = self._scale * factor
        new_scale = max(self._min_scale, min(self._max_scale, new_scale))

        if new_scale != self._scale:
            self._scale = new_scale

            # Adjust offset to zoom toward mouse position
            scene_pos_after = self.canvas_to_scene(pos)
            self._offset_x += (scene_pos_after.x() - scene_pos_before.x()) * self._scale
            self._offset_y += (scene_pos_after.y() - scene_pos_before.y()) * self._scale

            self.update()

    def keyPressEvent(self, event) -> None:
        """Handle keyboard input."""
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            # Delete selected
            if self._selected_block_id:
                self.remove_block(self._selected_block_id)
            elif self._selected_connection_id:
                self.remove_connection(self._selected_connection_id)

        elif event.key() == Qt.Key_Escape:
            # Cancel connection drawing
            if self._drag_mode == "connect":
                if self._connect_target_port:
                    self._connect_target_port.set_hovered(False)
                    self._connect_target_port.set_connect_valid(None)
                self._connect_from_port = None
                self._connect_preview_end = None
                self._connect_target_port = None
                self._connect_valid = None
                self._drag_mode = None
                self.setCursor(Qt.ArrowCursor)
                self.update()

        elif event.key() == Qt.Key_F:
            # Zoom to fit
            self.zoom_to_fit()

        else:
            super().keyPressEvent(event)

    # --- Helper Methods ---

    def _find_block_at(self, point: QPointF) -> Optional[BlockBase]:
        """Find block at scene point."""
        # Check in reverse order (top-most first)
        for block in reversed(list(self._blocks.values())):
            if block.contains(point):
                return block
        return None

    def _find_port_at(self, point: QPointF) -> Optional[Port]:
        """Find port at scene point."""
        for block in self._blocks.values():
            port = block.port_at(point)
            if port:
                return port
        return None

    def _find_connection_at(self, point: QPointF) -> Optional[Connection]:
        """Find connection at scene point."""
        for conn in self._connections.values():
            if conn.contains(point):
                return conn
        return None

    def _update_hover(self, scene_pos: QPointF) -> None:
        """Update hover state for blocks and ports."""
        # Check ports first
        port = self._find_port_at(scene_pos)
        if port != self._hovered_port:
            if self._hovered_port:
                self._hovered_port.set_hovered(False)
            self._hovered_port = port
            if port:
                port.set_hovered(True)
                self.setCursor(Qt.CrossCursor if port.is_output else Qt.PointingHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

        # Check blocks
        block = self._find_block_at(scene_pos)
        block_id = block.block_id if block else None
        if block_id != self._hovered_block_id:
            if self._hovered_block_id:
                prev_block = self._blocks.get(self._hovered_block_id)
                if prev_block:
                    prev_block.set_hovered(False)
            self._hovered_block_id = block_id
            if block:
                block.set_hovered(True)
                if not self._hovered_port:
                    self.setCursor(Qt.SizeAllCursor)

        # Check connections
        if not port and not block:
            conn = self._find_connection_at(scene_pos)
            conn_id = conn.connection_id if conn else None
            if conn_id != self._hovered_connection_id:
                if self._hovered_connection_id:
                    prev_conn = self._connections.get(self._hovered_connection_id)
                    if prev_conn:
                        prev_conn.set_hovered(False)
                self._hovered_connection_id = conn_id
                if conn:
                    conn.set_hovered(True)
                    self.setCursor(Qt.PointingHandCursor)

        self.update()

    def _update_connect_target(self, target_port: Optional[Port]) -> None:
        """
        Update connection target during drag.

        Checks validity and updates visual feedback.

        Args:
            target_port: Port currently under cursor (or None)
        """
        # Clear previous target hover state
        if self._connect_target_port and self._connect_target_port != target_port:
            self._connect_target_port.set_hovered(False)
            self._connect_target_port.set_connect_valid(None)

        self._connect_target_port = target_port

        if target_port is None:
            # No target - preview line uses source port color
            self._connect_valid = None
            self.setCursor(Qt.CrossCursor)
            return

        # Highlight the target port
        target_port.set_hovered(True)

        # Check validity:
        # 1. Must be an INPUT port (we're dragging from OUTPUT)
        # 2. Must be on a different block
        # 3. Port types must be compatible
        if not target_port.is_input:
            self._connect_valid = False
            target_port.set_connect_valid(False)
            self.setCursor(Qt.ForbiddenCursor)
            return

        if target_port.parent_block_id == self._connect_from_port.parent_block_id:
            self._connect_valid = False
            target_port.set_connect_valid(False)
            self.setCursor(Qt.ForbiddenCursor)
            return

        if not can_connect(self._connect_from_port.port_type, target_port.port_type):
            self._connect_valid = False
            target_port.set_connect_valid(False)
            self.setCursor(Qt.ForbiddenCursor)
            return

        # Valid connection target
        self._connect_valid = True
        target_port.set_connect_valid(True)
        self.setCursor(Qt.PointingHandCursor)

    def _open_block_config(self, block: BlockBase) -> None:
        """Open configuration dialog for a block."""
        dialog = block.get_config_dialog(self)
        if dialog:
            if dialog.exec():
                # Get config from dialog and apply
                if hasattr(dialog, "get_config"):
                    config = dialog.get_config()
                    block.apply_config(config)
                    self.block_configured.emit(block.block_id, config)
                    self.diagram_changed.emit()
                    self.update()

    def _show_context_menu(self, pos: QPointF) -> None:
        """Show context menu."""
        scene_pos = self.canvas_to_scene(pos)
        block = self._find_block_at(scene_pos)
        conn = self._find_connection_at(scene_pos)

        menu = QMenu(self)

        if block:
            menu.addAction("Configure...", lambda: self._open_block_config(block))
            menu.addAction("Delete Block", lambda: self.remove_block(block.block_id))
            menu.addSeparator()

        if conn:
            menu.addAction("Delete Connection", lambda: self.remove_connection(conn.connection_id))
            menu.addSeparator()

        menu.addAction("Zoom to Fit", self.zoom_to_fit)
        menu.addAction("Toggle Grid", lambda: self.set_grid_enabled(not self._grid.enabled))

        menu.exec(self.mapToGlobal(pos.toPoint()))
