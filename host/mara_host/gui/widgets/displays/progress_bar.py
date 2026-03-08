# mara_host/gui/widgets/displays/progress_bar.py
"""
Progress indicator widget.

Combines a progress bar with status text display.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
)


class ProgressIndicator(QWidget):
    """
    Progress bar with status text.

    Combines a progress bar with a status message for workflow progress.

    Example:
        progress = ProgressIndicator()
        progress.setProgress(50, "Processing...")
        progress.setIndeterminate("Waiting...")
        progress.complete("Done!")
    """

    def __init__(
        self,
        show_percentage: bool = True,
        parent=None,
    ):
        """
        Initialize progress indicator.

        Args:
            show_percentage: Show percentage text
            parent: Parent widget
        """
        super().__init__(parent)

        self._show_percentage = show_percentage
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        # Status row
        status_row = QHBoxLayout()
        status_row.setSpacing(8)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        status_row.addWidget(self._status_label, 1)

        if self._show_percentage:
            self._percent_label = QLabel("0%")
            self._percent_label.setStyleSheet(
                "font-family: 'Menlo', 'JetBrains Mono', monospace; "
                "color: #71717A; "
                "font-size: 11px;"
            )
            status_row.addWidget(self._percent_label)
        else:
            self._percent_label = None

        layout.addLayout(status_row)

    def setProgress(self, percent: int, status: str = "") -> None:
        """
        Set progress and status.

        Args:
            percent: Progress percentage (0-100)
            status: Status message
        """
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(percent)
        self._status_label.setText(status)

        if self._percent_label:
            self._percent_label.setText(f"{percent}%")

    def setIndeterminate(self, status: str = "") -> None:
        """
        Set indeterminate (spinning) progress.

        Args:
            status: Status message
        """
        self._progress_bar.setRange(0, 0)
        self._status_label.setText(status)

        if self._percent_label:
            self._percent_label.setText("")

    def complete(self, status: str = "Complete") -> None:
        """
        Mark as complete.

        Args:
            status: Completion message
        """
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._status_label.setText(status)
        self._status_label.setStyleSheet("color: #22C55E; font-size: 12px;")

        if self._percent_label:
            self._percent_label.setText("100%")

    def error(self, status: str = "Error") -> None:
        """
        Mark as error.

        Args:
            status: Error message
        """
        self._progress_bar.setRange(0, 100)
        self._status_label.setText(status)
        self._status_label.setStyleSheet("color: #EF4444; font-size: 12px;")

    def reset(self) -> None:
        """Reset to initial state."""
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._status_label.setText("")
        self._status_label.setStyleSheet("color: #A1A1AA; font-size: 12px;")

        if self._percent_label:
            self._percent_label.setText("0%")

    def value(self) -> int:
        """Get current progress value."""
        return self._progress_bar.value()

    def status(self) -> str:
        """Get current status text."""
        return self._status_label.text()
