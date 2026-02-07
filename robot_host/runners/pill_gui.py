# robot_host/runners/pill_gui_qt.py

from __future__ import annotations

import asyncio
import threading
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
    QMessageBox,
    QTabWidget,
    QGroupBox,
    QPlainTextEdit,
    QStatusBar,
    QTimeEdit,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QTimer, QTime, QDateTime, Signal, QObject

from robot_host.core.event_bus import EventBus
from robot_host.command.client import AsyncRobotClient
from robot_host.transport.serial_transport import SerialTransport
from robot_host.transport.tcp_transport import AsyncTcpTransport

from robot_host.module.pill_test import PillCarousel, PillCarouselConfig


# ==================== BASIC CONFIG ====================

TRANSPORT_TYPE = "serial"  # "serial" or "tcp"

# Serial settings
SERIAL_PORT = "/dev/cu.usbserial-0001"
SERIAL_BAUD = 115200

# TCP settings
TCP_STA = "10.0.0.60"
TCP_HOST = "192.168.4.1"
TCP_PORT = 3333

# Carousel config
MOTOR_ID = 0
STEPS_PER_REV = 200
SLOTS_PER_REV = 5
SPEED_RPS = 0.5
COVER_OFFSET_STEPS = 17

# One medication = advance by 1 slot (40 steps)
SLOTS_PER_DISPENSE = 1

APP_STYLESHEET = """
QMainWindow {
    background-color: #F4F5F7;
}

/* Tabs */
QTabWidget::pane {
    border: none;
}
QTabBar::tab {
    background: #E0E0E6;
    border-radius: 16px;
    padding: 8px 18px;
    margin-right: 4px;
    font-weight: 500;
    color: #4B5563;
}
QTabBar::tab:selected {
    background: #22C55E;
    color: white;
}

/* Header card */
QGroupBox#HeaderBox {
    background-color: #FFFFFF;
    border-radius: 20px;
    border: 1px solid #E5E7EB;
    margin-top: 4px;
}
QGroupBox#HeaderBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0;
}

/* Generic card-like groups */
QGroupBox {
    background-color: #FFFFFF;
    border-radius: 16px;
    margin-top: 16px;
    border: 1px solid #E5E7EB;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 4px 8px;
    background-color: transparent;
    color: #111827;
    font-weight: 600;
}

/* Labels & text */
QLabel {
    color: #111827;
}

/* Header status label */
QLabel#HeaderStatusLabel {
    font-weight: 600;
}

/* Buttons */
QPushButton {
    border-radius: 20px;
    padding: 10px 18px;
    font-weight: 600;
    border: none;
    background-color: #22C55E;
    color: white;
}
QPushButton:hover {
    background-color: #16A34A;
}
QPushButton:disabled {
    background-color: #D1D5DB;
}

/* Secondary buttons */
QPushButton#secondaryButton {
    background-color: #E5E7EB;
    color: #111827;
}
QPushButton#secondaryButton:hover {
    background-color: #D1D5DB;
}

/* Spinboxes / time edit */
QSpinBox, QDoubleSpinBox, QTimeEdit {
    border-radius: 10px;
    padding: 4px 6px;
    border: 1px solid #D1D5DB;
    background-color: #F9FAFB;
    color: #000000;
}

/* Log box */
QPlainTextEdit {
    border-radius: 12px;
    border: 1px solid #E5E7EB;
    background-color: #FFFFFF;
    color: #111827;
}

/* Status bar */
QStatusBar {
    background-color: #E5E7EB;
}
"""


async def tcp_preflight(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
    except Exception:
        return False
    else:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True


# ==================== ROBOT CONTROLLER (ASYNC SIDE) ====================

class RobotController:
    """
    Runs on the asyncio loop thread.
    Exposes high-level operations for the GUI.
    """

    def __init__(self, log_fn: Optional[Callable[[str], None]] = None):
        self.client: Optional[AsyncRobotClient] = None
        self.carousel: Optional[PillCarousel] = None
        self.connected: bool = False

        self.next_slot: int = 0
        self._dispense_initialized: bool = False

        # callback to log messages back to GUI thread
        self.log_fn = log_fn or (lambda msg: None)

    def _log(self, msg: str) -> None:
        # No stdout printing here by default; only GUI log to keep things light.
        self.log_fn(msg)

    async def connect(self):
        if self.connected:
            return

        bus = EventBus()

        if TRANSPORT_TYPE == "tcp":
            ok = await tcp_preflight(TCP_STA, TCP_PORT, timeout=1.0)
            if not ok:
                raise RuntimeError("TCP endpoint not reachable")
            self._log(f"[PillGUI] Using TCP transport to {TCP_STA}:{TCP_PORT}")
            transport = AsyncTcpTransport(host=TCP_STA, port=TCP_PORT)
        else:
            self._log(f"[PillGUI] Using SERIAL transport on {SERIAL_PORT} @ {SERIAL_BAUD}")
            transport = SerialTransport(port=SERIAL_PORT, baudrate=SERIAL_BAUD)

        self.client = AsyncRobotClient(transport=transport, bus=bus)

        self._log("[PillGUI] Connecting client...")
        await self.client.start()
        self._log("[PillGUI] Client started")

        config = PillCarouselConfig(
            motor_id=MOTOR_ID,
            steps_per_rev=STEPS_PER_REV,
            slots_per_rev=SLOTS_PER_REV,
            default_speed_rps=SPEED_RPS,
            cover_offset_steps=COVER_OFFSET_STEPS,
        )
        self.carousel = PillCarousel(self.client, config)

        await self.carousel.init_robot(telem_interval_ms=500)
        self.carousel.set_current_slot(0)

        self.next_slot = 0
        self._dispense_initialized = True
        self.connected = True
        self._log("[PillGUI] Robot controller initialized at slot 0")

    async def shutdown(self):
        if not self.connected:
            return
        try:
            if self.carousel:
                self._log("[PillGUI] Shutting down carousel...")
                await self.carousel.shutdown_robot()
            if self.client:
                self._log("[PillGUI] Stopping client...")
                await self.client.stop()
        finally:
            self.connected = False
            self._log("[PillGUI] Robot controller shut down")

    # ----- High-level operations -----

    async def dispense_slots(self, start_slot: int, count: int, delay_sec: float = 0.0):
        """
        Dispense `count` meds.

        - First time: use GUI `start_slot` as initial logical position.
        - Each pill = advance by 1 slot (40 steps).
        """
        await self.connect()

        if delay_sec > 0:
            self._log(f"[PillGUI] Waiting {delay_sec:.1f} seconds before dispensing...")
            await asyncio.sleep(delay_sec)

        total_slots = self.carousel.config.slots_per_rev

        # On the very first dispense, align logical cycle to GUI start slot
        if not self._dispense_initialized:
            self.next_slot = start_slot % total_slots
            self._dispense_initialized = True
            self._log(f"[PillGUI] Initializing next_slot from GUI start_slot={self.next_slot}")

        slot = self.next_slot

        for i in range(count):
            self._log(f"[PillGUI] Dispense {i+1}/{count} at slot {slot}")
            await self.carousel.goto_slot(slot)
            await asyncio.sleep(1.0)  # drop / settle time

            # Advance to next slot (1 slot = 40 steps)
            slot = (slot + SLOTS_PER_DISPENSE) % total_slots

        self.next_slot = slot
        self._log(f"[PillGUI] Dispense sequence complete, next_slot={self.next_slot}")

    async def goto_slot(self, slot: int):
        await self.connect()
        slot = slot % self.carousel.config.slots_per_rev
        self._log(f"[PillGUI] Manual goto_slot({slot})")
        await self.carousel.goto_slot(slot)

    async def step_next_slot(self):
        await self.connect()
        total_slots = self.carousel.config.slots_per_rev
        target = (self.carousel.current_slot + 1) % total_slots
        self._log(f"[PillGUI] Manual next slot -> {target}")
        await self.carousel.goto_slot(target)

    async def step_prev_slot(self):
        await self.connect()
        total_slots = self.carousel.config.slots_per_rev
        target = (self.carousel.current_slot - 1) % total_slots
        self._log(f"[PillGUI] Manual prev slot -> {target}")
        await self.carousel.goto_slot(target)

    async def spin_full_rev(self):
        await self.connect()
        self._log("[PillGUI] Manual full revolution")
        await self.carousel.spin_full_rev()

    async def recalibrate_current(self, as_slot: int = 0):
        """
        Treat the current physical position as logical slot `as_slot`.
        """
        await self.connect()
        total_slots = self.carousel.config.slots_per_rev
        as_slot = as_slot % total_slots
        self.carousel.set_current_slot(as_slot)
        self.next_slot = as_slot
        self._log(f"[PillGUI] Recalibrated: current position = slot {as_slot}")


# ==================== GUI SIGNALS (THREAD-SAFE LOGGING) ====================

class GuiSignals(QObject):
    log_message = Signal(str)
    status_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)


# ==================== QT MAIN WINDOW ====================

class PillDispenserWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Pill Dispenser")
        self.signals = GuiSignals()

        # Default font
        self.setFont(QFont("SF Pro Text", 11))

        # Central layout
        central = QWidget()
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(16, 16, 16, 8)
        central_layout.setSpacing(12)
        central.setLayout(central_layout)
        self.setCentralWidget(central)

        # ---- Header bar ----
        header = QGroupBox()
        header.setObjectName("HeaderBox")
        header_layout = QHBoxLayout()
        header.setLayout(header_layout)
        header.setTitle("")

        title_label = QLabel("Pill Dispenser")
        title_font = QFont("SF Pro Display", 18, QFont.Bold)
        title_label.setFont(title_font)

        self.header_status_label = QLabel("Connecting to device…")
        self.header_status_label.setObjectName("HeaderStatusLabel")
        self.header_status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        header_layout.addWidget(title_label, stretch=1)
        header_layout.addWidget(self.header_status_label, stretch=1)

        # ---- Tabs ----
        self.tab_widget = QTabWidget()

        # Log area & status bar
        self.log_widget = QPlainTextEdit()
        self.log_widget.setReadOnly(True)

        log_container = QWidget()
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.addWidget(QLabel("Event Log"))
        log_layout.addWidget(self.log_widget)
        log_container.setLayout(log_layout)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Add header + tabs
        central_layout.addWidget(header)
        central_layout.addWidget(self.tab_widget, stretch=1)

        # Asyncio loop in background thread
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(
            target=self.loop.run_forever,
            daemon=True,
        )
        self.loop_thread.start()

        # Robot controller with log callback
        self.controller = RobotController(log_fn=self._log_from_controller)

        # Build tabs
        self._build_tabs(log_container)

        # Wire signals
        self.signals.log_message.connect(self._append_log)
        self.signals.status_message.connect(self._set_status)

        # Kick off connection
        fut = asyncio.run_coroutine_threadsafe(
            self.controller.connect(), self.loop
        )
        fut.add_done_callback(self._on_connect_done)

        self.resize(720, 480)

    # ---------- Tab building ----------

    def _build_tabs(self, log_container: QWidget):
        # Tab 1: Dispense
        dispense_tab = QWidget()
        dispense_layout = QVBoxLayout()
        dispense_layout.setContentsMargins(0, 0, 0, 0)
        dispense_layout.setSpacing(12)
        dispense_tab.setLayout(dispense_layout)

        # "Today's Dose" card
        main_group = QGroupBox("Today’s Dose")
        main_grid = QGridLayout()
        main_grid.setVerticalSpacing(10)
        main_grid.setHorizontalSpacing(10)

        # Start slot
        main_grid.addWidget(QLabel("Start slot:"), 0, 0)
        self.slot_spin = QSpinBox()
        self.slot_spin.setRange(0, SLOTS_PER_REV - 1)
        self.slot_spin.setValue(0)
        main_grid.addWidget(self.slot_spin, 0, 1)

        # # of meds
        main_grid.addWidget(QLabel("Number of pills:"), 1, 0)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 20)
        self.count_spin.setValue(1)
        main_grid.addWidget(self.count_spin, 1, 1)

        # Delay for immediate dispense
        main_grid.addWidget(QLabel("Delay (seconds):"), 2, 0)
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 3600.0)
        self.delay_spin.setDecimals(1)
        self.delay_spin.setSingleStep(5.0)
        self.delay_spin.setValue(0.0)
        main_grid.addWidget(self.delay_spin, 2, 1)

        # Schedule time (12-hour)
        main_grid.addWidget(QLabel("Schedule time:"), 3, 0)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("h:mm AP")  # e.g., 8:30 PM
        self.time_edit.setTime(QTime.currentTime())
        main_grid.addWidget(self.time_edit, 3, 1)

        # Primary buttons
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)

        self.dispense_btn = QPushButton("Dispense Now")
        self.dispense_btn.setMinimumHeight(38)

        self.schedule_btn = QPushButton("Schedule Dispense")
        self.schedule_btn.setObjectName("secondaryButton")
        self.schedule_btn.setMinimumHeight(38)

        self.dispense_btn.clicked.connect(self.on_dispense_clicked)
        self.schedule_btn.clicked.connect(self.on_schedule_clicked)

        buttons_row.addWidget(self.dispense_btn)
        buttons_row.addWidget(self.schedule_btn)

        main_grid.addLayout(buttons_row, 4, 0, 1, 2)

        # Info label
        self.next_slot_label = QLabel("Next logical slot: 0")
        self.next_slot_label.setStyleSheet("color: #666666;")
        main_grid.addWidget(self.next_slot_label, 5, 0, 1, 2)

        main_group.setLayout(main_grid)
        dispense_layout.addWidget(main_group)

        # Device status card
        status_group = QGroupBox("Device Status")
        status_layout = QVBoxLayout()
        status_layout.setSpacing(6)

        self.status_detail_label = QLabel("Connecting…")
        self.status_detail_label.setStyleSheet("color: #555555;")

        status_layout.addWidget(self.status_detail_label)

        small_hint = QLabel("Tip: Make sure the dispenser is plugged in and the lid is closed.")
        small_hint.setStyleSheet("color: #888888; font-size: 10pt;")
        status_layout.addWidget(small_hint)

        status_group.setLayout(status_layout)
        dispense_layout.addWidget(status_group)

        dispense_layout.addStretch(1)

        # Tab 2: Manual Control
        manual_tab = QWidget()
        manual_layout = QVBoxLayout()
        manual_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.setSpacing(12)
        manual_tab.setLayout(manual_layout)

        manual_group = QGroupBox("Manual Carousel Control")
        mg = QGridLayout()
        mg.setVerticalSpacing(10)
        mg.setHorizontalSpacing(10)

        # Goto slot
        mg.addWidget(QLabel("Go to slot:"), 0, 0)
        self.manual_slot_spin = QSpinBox()
        self.manual_slot_spin.setRange(0, SLOTS_PER_REV - 1)
        self.manual_slot_spin.setValue(0)
        mg.addWidget(self.manual_slot_spin, 0, 1)
        goto_btn = QPushButton("Go")
        goto_btn.setObjectName("secondaryButton")
        goto_btn.clicked.connect(self.on_manual_goto)
        mg.addWidget(goto_btn, 0, 2)

        # Next / Prev
        next_btn = QPushButton("Next slot")
        next_btn.setObjectName("secondaryButton")
        prev_btn = QPushButton("Previous slot")
        prev_btn.setObjectName("secondaryButton")
        next_btn.clicked.connect(self.on_manual_next)
        prev_btn.clicked.connect(self.on_manual_prev)
        mg.addWidget(prev_btn, 1, 0)
        mg.addWidget(next_btn, 1, 1)

        # Full revolution
        full_btn = QPushButton("Spin full revolution")
        full_btn.setObjectName("secondaryButton")
        full_btn.clicked.connect(self.on_manual_full_rev)
        mg.addWidget(full_btn, 2, 0, 1, 3)

        # Recalibrate
        recal_btn = QPushButton("Set current as slot 0")
        recal_btn.setObjectName("secondaryButton")
        recal_btn.clicked.connect(self.on_manual_recalibrate)
        mg.addWidget(recal_btn, 3, 0, 1, 3)

        manual_group.setLayout(mg)
        manual_layout.addWidget(manual_group)
        manual_layout.addStretch(1)

        # Tab 3: Logs / Status
        log_tab = log_container

        self.tab_widget.addTab(dispense_tab, "Dispense")
        self.tab_widget.addTab(manual_tab, "Manual Control")
        self.tab_widget.addTab(log_tab, "Logs")

    # ---------- Logging / status helpers ----------

    def _log_from_controller(self, msg: str):
        # Called from async thread
        self.signals.log_message.emit(msg)

    def _append_log(self, msg: str):
        self.log_widget.appendPlainText(msg)
        # Keep the log from getting huge
        max_blocks = 300
        doc = self.log_widget.document()
        if doc.blockCount() > max_blocks:
            self.log_widget.clear()

    def _set_status(self, text: str):
        # Detailed text for status bar + Device Status card
        self.status_bar.showMessage(text)
        self.status_detail_label.setText(text)

        # Short, user-friendly header text + color
        lower = text.lower()
        if "error" in lower or "could not open" in lower:
            header_text = "Not connected"
            color = "#B91C1C"   # red
        elif "connected" in lower:
            header_text = "Connected"
            color = "#15803D"   # green
        elif "dispens" in lower:
            header_text = "Dispensing…"
            color = "#0F766E"   # teal
        elif "scheduled" in lower:
            header_text = "Dose scheduled"
            color = "#4B5563"   # neutral
        else:
            header_text = text
            color = "#4B5563"

        self.header_status_label.setText(header_text)
        self.header_status_label.setStyleSheet(
            f"color: {color}; font-weight: 600;"
        )

    def _on_connect_done(self, fut: "asyncio.Future"):
        try:
            fut.result()
            self.signals.status_message.emit("Connected")
            self._update_next_slot_label()
        except Exception as e:
            msg = f"Connection error: {e}"
            self.signals.status_message.emit(msg)
            self._append_log(f"[PillGUI] {msg}")

    def _update_next_slot_label(self):
        self.next_slot_label.setText(
            f"Next logical slot: {self.controller.next_slot}"
        )

    # ---------- Button handlers ----------

    def on_dispense_clicked(self):
        slot = self.slot_spin.value()
        count = self.count_spin.value()
        delay = self.delay_spin.value()

        self.signals.status_message.emit(
            f"Dispensing: slot {slot}, count {count}, delay {delay:.1f}s"
        )
        self._append_log(
            f"[PillGUI] GUI requested dispense: slot={slot}, count={count}, delay={delay:.1f}s"
        )

        fut = asyncio.run_coroutine_threadsafe(
            self.controller.dispense_slots(slot, count, delay),
            self.loop,
        )

        def done_callback(f: "asyncio.Future"):
            try:
                f.result()
                self.signals.status_message.emit("Dispense complete")
            except Exception as e:
                self._append_log(f"[PillGUI] Error during dispense: {e}")
                self.signals.status_message.emit(f"Error: {e}")
            QTimer.singleShot(0, self._update_next_slot_label)

        fut.add_done_callback(done_callback)

    def on_manual_goto(self):
        slot = self.manual_slot_spin.value()
        self._append_log(f"[PillGUI] GUI manual goto slot {slot}")
        fut = asyncio.run_coroutine_threadsafe(
            self.controller.goto_slot(slot),
            self.loop,
        )
        fut.add_done_callback(lambda f: None)

    def on_manual_next(self):
        self._append_log("[PillGUI] GUI manual next slot")
        fut = asyncio.run_coroutine_threadsafe(
            self.controller.step_next_slot(),
            self.loop,
        )
        fut.add_done_callback(lambda f: None)

    def on_manual_prev(self):
        self._append_log("[PillGUI] GUI manual prev slot")
        fut = asyncio.run_coroutine_threadsafe(
            self.controller.step_prev_slot(),
            self.loop,
        )
        fut.add_done_callback(lambda f: None)

    def on_manual_full_rev(self):
        self._append_log("[PillGUI] GUI manual full revolution")
        fut = asyncio.run_coroutine_threadsafe(
            self.controller.spin_full_rev(),
            self.loop,
        )
        fut.add_done_callback(lambda f: None)

    def on_manual_recalibrate(self):
        reply = QMessageBox.question(
            self,
            "Recalibrate",
            "Treat the current physical position as Slot 0?\n"
            "This will reset the internal next-slot pointer.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._append_log("[PillGUI] GUI recalibrate current as slot 0")
        fut = asyncio.run_coroutine_threadsafe(
            self.controller.recalibrate_current(as_slot=0),
            self.loop,
        )

        def done_callback(f: "asyncio.Future"):
            try:
                f.result()
                QTimer.singleShot(0, self._update_next_slot_label)
            except Exception as e:
                self._append_log(f"[PillGUI] Error recalibrating: {e}")
                self.signals.status_message.emit(f"Error: {e}")

        fut.add_done_callback(done_callback)

    def on_schedule_clicked(self):
        """
        Schedule a dispense at the selected time (today or tomorrow).
        Uses the current Start slot and # of meds from the GUI.
        """
        slot = self.slot_spin.value()
        count = self.count_spin.value()
        when_time: QTime = self.time_edit.time()

        now = QDateTime.currentDateTime()
        target = QDateTime(now.date(), when_time)
        if target <= now:
            target = target.addDays(1)

        msec_until = now.msecsTo(target)

        self._append_log(
            f"[PillGUI] Scheduling dispense at "
            f"{target.toString('yyyy-MM-dd h:mm AP')} "
            f"(in {msec_until/1000:.1f}s) - slot={slot}, count={count}"
        )
        self.signals.status_message.emit(
            f"Scheduled dispense at {target.toString('h:mm AP')} "
            f"(slot {slot}, {count} meds)"
        )

        def _fire():
            self._append_log(
                f"[PillGUI] Executing scheduled dispense: slot={slot}, count={count}"
            )
            fut = asyncio.run_coroutine_threadsafe(
                self.controller.dispense_slots(slot, count, 0.0),
                self.loop,
            )

            def done_callback(f: "asyncio.Future"):
                try:
                    f.result()
                    self.signals.status_message.emit("Scheduled dispense complete")
                except Exception as e:
                    self._append_log(f"[PillGUI] Error during scheduled dispense: {e}")
                    self.signals.status_message.emit(f"Error: {e}")
                QTimer.singleShot(0, self._update_next_slot_label)

            fut.add_done_callback(done_callback)

        QTimer.singleShot(msec_until, _fire)

    # ---------- Qt lifecycle ----------

    def closeEvent(self, event):
        self._append_log("[PillGUI] Shutting down...")
        asyncio.run_coroutine_threadsafe(self.controller.shutdown(), self.loop)
        self.loop.call_soon_threadsafe(self.loop.stop)
        event.accept()


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    win = PillDispenserWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
