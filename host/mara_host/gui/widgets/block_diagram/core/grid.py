# mara_host/gui/widgets/block_diagram/core/grid.py
"""Grid rendering and snap-to-grid functionality."""

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainter, QPen, QColor


class Grid:
    """
    Grid system for the diagram canvas.

    Provides:
    - Snap-to-grid positioning
    - Grid rendering with major/minor lines
    - Coordinate transformations
    """

    def __init__(
        self,
        grid_size: int = 20,
        major_interval: int = 5,
        enabled: bool = True,
    ):
        """
        Initialize grid.

        Args:
            grid_size: Size of grid cells in pixels
            major_interval: Number of minor cells per major grid line
            enabled: Whether snap-to-grid is enabled
        """
        self.grid_size = grid_size
        self.major_interval = major_interval
        self.enabled = enabled

        # Colors
        self.minor_color = QColor("#1F1F23")  # Very subtle
        self.major_color = QColor("#27272A")  # Slightly more visible

    def snap(self, point: QPointF) -> QPointF:
        """
        Snap a point to the nearest grid intersection.

        Args:
            point: Point to snap

        Returns:
            Snapped point (or original if grid disabled)
        """
        if not self.enabled:
            return point

        x = round(point.x() / self.grid_size) * self.grid_size
        y = round(point.y() / self.grid_size) * self.grid_size
        return QPointF(x, y)

    def snap_x(self, x: float) -> float:
        """Snap x coordinate to grid."""
        if not self.enabled:
            return x
        return round(x / self.grid_size) * self.grid_size

    def snap_y(self, y: float) -> float:
        """Snap y coordinate to grid."""
        if not self.enabled:
            return y
        return round(y / self.grid_size) * self.grid_size

    def paint(
        self,
        painter: QPainter,
        width: int,
        height: int,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        scale: float = 1.0,
    ) -> None:
        """
        Paint the grid.

        Args:
            painter: QPainter to draw with
            width: Canvas width
            height: Canvas height
            offset_x: Pan offset X
            offset_y: Pan offset Y
            scale: Zoom scale
        """
        # Calculate grid parameters based on zoom
        effective_grid = self.grid_size * scale

        # Don't draw grid if too small
        if effective_grid < 5:
            return

        major_size = self.grid_size * self.major_interval
        effective_major = major_size * scale

        # Calculate starting positions (accounting for pan)
        start_x = int(-offset_x % effective_grid)
        start_y = int(-offset_y % effective_grid)

        # Draw minor grid lines
        if effective_grid >= 10:  # Only draw if visible
            painter.setPen(QPen(self.minor_color, 1))

            # Vertical lines
            x = start_x
            while x < width:
                painter.drawLine(int(x), 0, int(x), height)
                x += effective_grid

            # Horizontal lines
            y = start_y
            while y < height:
                painter.drawLine(0, int(y), width, int(y))
                y += effective_grid

        # Draw major grid lines
        start_major_x = int(-offset_x % effective_major)
        start_major_y = int(-offset_y % effective_major)

        painter.setPen(QPen(self.major_color, 1))

        # Vertical major lines
        x = start_major_x
        while x < width:
            painter.drawLine(int(x), 0, int(x), height)
            x += effective_major

        # Horizontal major lines
        y = start_major_y
        while y < height:
            painter.drawLine(0, int(y), width, int(y))
            y += effective_major
