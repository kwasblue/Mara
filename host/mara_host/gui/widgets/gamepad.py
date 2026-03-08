# mara_host/gui/widgets/gamepad.py
"""
Gamepad input handler for physical controller support.

Supports Xbox, PlayStation, and generic USB controllers.
"""

from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


class GamepadHandler(QObject):
    """
    Handles gamepad input and emits signals for stick/button events.

    Uses pygame for cross-platform gamepad support.

    Signals:
        left_stick(x, y): Left stick position (-1 to 1)
        right_stick(x, y): Right stick position (-1 to 1)
        button_pressed(button): Button pressed (A, B, X, Y, LB, RB, etc.)
        button_released(button): Button released
        connected(name): Controller connected
        disconnected(): Controller disconnected
    """

    # Signals
    left_stick = Signal(float, float)
    right_stick = Signal(float, float)
    button_pressed = Signal(str)
    button_released = Signal(str)
    connected = Signal(str)
    disconnected = Signal()

    # Button mappings (Xbox layout)
    BUTTON_MAP = {
        0: "A",
        1: "B",
        2: "X",
        3: "Y",
        4: "LB",
        5: "RB",
        6: "Back",
        7: "Start",
        8: "LS",  # Left stick click
        9: "RS",  # Right stick click
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self._joystick: Optional[object] = None
        self._running = False
        self._deadzone = 0.15
        self._poll_rate = 50  # Hz

        # Last known stick values
        self._last_left = (0.0, 0.0)
        self._last_right = (0.0, 0.0)

        # Poll timer
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)

        if HAS_PYGAME:
            pygame.init()
            pygame.joystick.init()

    @property
    def is_available(self) -> bool:
        """Check if pygame is available."""
        return HAS_PYGAME

    @property
    def is_connected(self) -> bool:
        """Check if a gamepad is connected."""
        return self._joystick is not None

    @property
    def deadzone(self) -> float:
        """Get stick deadzone."""
        return self._deadzone

    @deadzone.setter
    def deadzone(self, value: float) -> None:
        """Set stick deadzone (0-1)."""
        self._deadzone = max(0.0, min(1.0, value))

    def start(self) -> bool:
        """Start polling for gamepad input."""
        if not HAS_PYGAME:
            return False

        # Try to connect to first available joystick
        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()
            self.connected.emit(self._joystick.get_name())
        else:
            return False

        self._running = True
        self._poll_timer.start(1000 // self._poll_rate)
        return True

    def stop(self) -> None:
        """Stop polling."""
        self._running = False
        self._poll_timer.stop()

        if self._joystick:
            self._joystick.quit()
            self._joystick = None

    def _poll(self) -> None:
        """Poll gamepad state."""
        if not HAS_PYGAME or not self._joystick:
            return

        # Process pygame events
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                btn_name = self.BUTTON_MAP.get(event.button, f"Button{event.button}")
                self.button_pressed.emit(btn_name)

            elif event.type == pygame.JOYBUTTONUP:
                btn_name = self.BUTTON_MAP.get(event.button, f"Button{event.button}")
                self.button_released.emit(btn_name)

            elif event.type == pygame.JOYDEVICEREMOVED:
                self._joystick = None
                self.disconnected.emit()
                return

            elif event.type == pygame.JOYDEVICEADDED:
                if not self._joystick:
                    self._joystick = pygame.joystick.Joystick(event.device_index)
                    self._joystick.init()
                    self.connected.emit(self._joystick.get_name())

        if not self._joystick:
            return

        # Read stick values
        left_x = self._apply_deadzone(self._joystick.get_axis(0))
        left_y = self._apply_deadzone(-self._joystick.get_axis(1))  # Invert Y

        right_x = self._apply_deadzone(self._joystick.get_axis(2))
        right_y = self._apply_deadzone(-self._joystick.get_axis(3))  # Invert Y

        # Emit if changed
        left = (left_x, left_y)
        right = (right_x, right_y)

        if left != self._last_left:
            self._last_left = left
            self.left_stick.emit(left_x, left_y)

        if right != self._last_right:
            self._last_right = right
            self.right_stick.emit(right_x, right_y)

    def _apply_deadzone(self, value: float) -> float:
        """Apply deadzone to stick value."""
        if abs(value) < self._deadzone:
            return 0.0

        # Rescale to 0-1 range outside deadzone
        sign = 1.0 if value > 0 else -1.0
        return sign * (abs(value) - self._deadzone) / (1.0 - self._deadzone)

    def get_connected_name(self) -> Optional[str]:
        """Get name of connected controller."""
        if self._joystick:
            return self._joystick.get_name()
        return None

    @staticmethod
    def list_controllers() -> list[str]:
        """List available controllers."""
        if not HAS_PYGAME:
            return []

        pygame.joystick.init()
        controllers = []
        for i in range(pygame.joystick.get_count()):
            js = pygame.joystick.Joystick(i)
            controllers.append(js.get_name())
        return controllers
