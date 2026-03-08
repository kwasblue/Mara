# mara_host/gui/panels/advanced/slot_base.py
"""
Base classes for slot-based control panels.

Provides common patterns for controller/observer slot widgets and tab panels.
"""

from abc import abstractmethod
from typing import Type

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QCheckBox,
    QScrollArea,
)
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController


class SlotWidgetBase(QFrame):
    """
    Base class for slot configuration widgets.

    Provides common structure:
    - Header with title and enabled checkbox
    - Info frame (hidden when unconfigured)
    - Button row with Configure and Reset

    Subclasses implement:
    - _setup_info_frame(): Add slot-specific info labels
    - _setup_buttons(): Add slot-specific buttons
    - _configure(): Show configuration dialog
    - _reset(): Reset slot state
    - _on_enable_changed(): Handle enable/disable
    """

    def __init__(
        self,
        slot: int,
        controller: RobotController,
        parent=None,
    ):
        super().__init__(parent)
        self.slot = slot
        self.robot_controller = controller
        self._configured = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { background-color: #1A1A1C; border-radius: 8px; padding: 12px; }"
        )

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        self.title_label = QLabel(f"Slot {self.slot}: [Unconfigured]")
        self.title_label.setStyleSheet("font-weight: bold; color: #FAFAFA;")
        header.addWidget(self.title_label)

        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.stateChanged.connect(self._handle_enable_changed)
        header.addWidget(self.enabled_check)
        header.addStretch()
        layout.addLayout(header)

        # Info frame (hidden when unconfigured)
        self.info_frame = QFrame()
        self._setup_info_frame()
        self.info_frame.setVisible(False)
        layout.addWidget(self.info_frame)

        # Button row
        btn_row = QHBoxLayout()
        self._setup_buttons(btn_row)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _setup_info_frame(self) -> None:
        """
        Set up the info frame with slot-specific labels.

        Override in subclass to add custom info labels.
        """
        pass

    def _setup_buttons(self, btn_row: QHBoxLayout) -> None:
        """
        Set up the button row.

        Override in subclass to add custom buttons.
        Default adds Configure and Reset buttons.
        """
        self.configure_btn = QPushButton("Configure")
        self.configure_btn.setObjectName("secondary")
        self.configure_btn.clicked.connect(self._configure)
        btn_row.addWidget(self.configure_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("secondary")
        self.reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(self.reset_btn)

    def _handle_enable_changed(self, state: int) -> None:
        """Handle checkbox state change."""
        enable = state == Qt.CheckState.Checked.value
        self._on_enable_changed(enable)

    @abstractmethod
    def _on_enable_changed(self, enable: bool) -> None:
        """
        Handle enable/disable.

        Args:
            enable: True if enabling, False if disabling
        """
        pass

    @abstractmethod
    def _configure(self) -> None:
        """Show configuration dialog."""
        pass

    def _reset(self) -> None:
        """Reset slot to unconfigured state."""
        self._configured = False
        self.title_label.setText(f"Slot {self.slot}: [Unconfigured]")
        self.info_frame.setVisible(False)
        self.enabled_check.setChecked(False)

    def _set_configured(self, title: str) -> None:
        """
        Mark slot as configured.

        Args:
            title: Title to display (e.g., "PID Controller")
        """
        self._configured = True
        self.title_label.setText(f"Slot {self.slot}: {title}")
        self.info_frame.setVisible(True)


class SlotTabPanel(QWidget):
    """
    Base class for slot-based tab panels.

    Provides common scroll area layout with multiple slot widgets.

    Subclasses set:
    - NUM_SLOTS: Number of slots to display
    - SLOT_WIDGET_CLASS: The slot widget class to instantiate
    - TITLE_FORMAT: Title format string (e.g., "Control Slots ({} available)")
    """

    NUM_SLOTS: int = 8
    SLOT_WIDGET_CLASS: Type[SlotWidgetBase] = None
    TITLE_FORMAT: str = "Slots ({} available)"

    def __init__(
        self,
        signals: GuiSignals,
        controller: RobotController,
        parent=None,
    ):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller
        self.slot_widgets = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = self.TITLE_FORMAT.format(self.NUM_SLOTS)
        info_label = QLabel(title)
        info_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #FAFAFA;")
        layout.addWidget(info_label)

        # Scroll area for slots
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)

        # Create slot widgets
        for i in range(self.NUM_SLOTS):
            if self.SLOT_WIDGET_CLASS is not None:
                slot_widget = self.SLOT_WIDGET_CLASS(i, self.controller)
                self.slot_widgets.append(slot_widget)
                scroll_layout.addWidget(slot_widget)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
