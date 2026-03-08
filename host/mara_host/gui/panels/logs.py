# mara_host/gui/panels/logs.py
"""
Logs panel for viewing application and robot events.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "logs",
    "label": "Logs",
    "order": 130,
}

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QComboBox,
    QCheckBox,
    QLineEdit,
)

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.gui.core.dev_mode import is_dev_mode


class LogsPanel(QWidget):
    """
    Logs panel for viewing events and messages.

    Features:
        - Filterable log display
        - Log level filtering
        - Search
        - Export
    """

    MAX_LOG_LINES = 1000

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

        self._log_count = 0
        self._filter_level = "ALL"
        self._filter_text = ""

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the logs panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Note: Log messages are forwarded by MainWindow._on_log_message()
        # to avoid duplicate signal connections

        # Filter bar
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        if is_dev_mode():
            self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        else:
            self.level_combo.addItems(["ALL", "INFO", "WARNING", "ERROR"])
        self.level_combo.currentTextChanged.connect(self._on_level_changed)
        filter_layout.addWidget(self.level_combo)

        filter_layout.addSpacing(20)

        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter messages...")
        self.search_input.textChanged.connect(self._on_search_changed)
        filter_layout.addWidget(self.search_input, 1)

        filter_layout.addSpacing(20)

        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        filter_layout.addWidget(self.auto_scroll_check)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondary")
        clear_btn.setMinimumWidth(70)
        clear_btn.clicked.connect(self._clear_logs)
        filter_layout.addWidget(clear_btn)

        layout.addLayout(filter_layout)

        # Log display
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(self.MAX_LOG_LINES)
        self.log_text.setStyleSheet(
            "font-family: 'Menlo', 'Consolas', 'Monaco', monospace; "
            "font-size: 12px;"
        )
        layout.addWidget(self.log_text, 1)

        # Stats bar
        stats_layout = QHBoxLayout()

        self.line_count_label = QLabel("0 messages")
        stats_layout.addWidget(self.line_count_label)

        stats_layout.addStretch()

        export_btn = QPushButton("Export Logs")
        export_btn.setObjectName("secondary")
        export_btn.setMinimumWidth(110)
        export_btn.clicked.connect(self._export_logs)
        stats_layout.addWidget(export_btn)

        layout.addLayout(stats_layout)

    def add_message(self, timestamp: str, level: str, message: str) -> None:
        """
        Add a log message.

        Args:
            timestamp: Message timestamp
            level: Log level (INFO, WARNING, ERROR)
            message: Log message
        """
        # Check filters
        if self._filter_level != "ALL" and level != self._filter_level:
            return

        if self._filter_text and self._filter_text.lower() not in message.lower():
            return

        # Format message
        level_colors = {
            "DEBUG": "#06B6D4",  # Cyan for debug
            "INFO": "#A1A1AA",
            "WARNING": "#F59E0B",
            "ERROR": "#EF4444",
        }
        color = level_colors.get(level, "#A1A1AA")

        formatted = f'<span style="color: #52525B;">{timestamp}</span> '
        formatted += f'<span style="color: {color};">[{level:7}]</span> '
        formatted += f'<span style="color: #FAFAFA;">{message}</span>'

        self.log_text.appendHtml(formatted)
        self._log_count += 1
        self.line_count_label.setText(f"{self._log_count} messages")

        # Auto-scroll
        if self.auto_scroll_check.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _on_level_changed(self, level: str) -> None:
        """Handle level filter change."""
        self._filter_level = level

    def _on_search_changed(self, text: str) -> None:
        """Handle search filter change."""
        self._filter_text = text

    def _clear_logs(self) -> None:
        """Clear all logs."""
        self.log_text.clear()
        self._log_count = 0
        self.line_count_label.setText("0 messages")

    def _export_logs(self) -> None:
        """Export logs to file."""
        from PySide6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            "mara_logs.txt",
            "Text Files (*.txt);;All Files (*)",
        )

        if filename:
            with open(filename, "w") as f:
                f.write(self.log_text.toPlainText())
            self.signals.status_message.emit(f"Logs exported to {filename}")
