# mara_host/core/connection_monitor.py
"""
Connection state machine with explicit state transitions and events.

Provides more granular connection state than simple connected/disconnected,
enabling better handling of reconnection scenarios.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, List


class ConnectionState(Enum):
    """Connection state machine states."""

    DISCONNECTED = "disconnected"  # No connection, not attempting to connect
    CONNECTING = "connecting"  # Initial connection in progress
    CONNECTED = "connected"  # Stable connection established
    RECONNECTING = "reconnecting"  # Lost connection, attempting to restore


@dataclass
class ConnectionEvent:
    """Event emitted on connection state transitions."""

    timestamp: float
    from_state: ConnectionState
    to_state: ConnectionState
    reason: str = ""


@dataclass
class ConnectionStats:
    """Statistics for connection monitoring."""

    messages_received: int = 0
    disconnects: int = 0
    reconnects: int = 0
    total_downtime_s: float = 0.0
    last_disconnect_time: Optional[float] = None


class ConnectionMonitor:
    """
    Monitors connection health based on incoming messages.

    Features:
    - Explicit state machine: DISCONNECTED -> CONNECTING -> CONNECTED <-> RECONNECTING
    - Event callbacks for state transitions
    - Connection statistics tracking
    - Integration with EventBus via on_message_received()

    State Transitions:
        DISCONNECTED -> CONNECTING: start() called
        CONNECTING -> CONNECTED: first message received
        CONNECTED -> RECONNECTING: timeout elapsed without message
        RECONNECTING -> CONNECTED: message received after timeout
        RECONNECTING -> DISCONNECTED: manual disconnect or too many failures
        CONNECTED -> DISCONNECTED: manual disconnect via reset()

    Example:
        monitor = ConnectionMonitor(
            timeout_s=1.0,
            on_state_change=lambda evt: print(f"{evt.from_state} -> {evt.to_state}")
        )

        await monitor.start_monitoring()

        # Call on each incoming message
        monitor.on_message_received()

        # Check current state
        if monitor.state == ConnectionState.CONNECTED:
            print("Connected!")
    """

    def __init__(
        self,
        timeout_s: float = 1.0,
        on_disconnect: Optional[Callable[[], None]] = None,
        on_reconnect: Optional[Callable[[], None]] = None,
        on_state_change: Optional[Callable[[ConnectionEvent], None]] = None,
    ):
        """
        Initialize connection monitor.

        Args:
            timeout_s: Time without messages before considering connection lost
            on_disconnect: Legacy callback for disconnect (CONNECTED -> RECONNECTING)
            on_reconnect: Legacy callback for reconnect (RECONNECTING -> CONNECTED)
            on_state_change: New callback for all state transitions
        """
        self.timeout_s = timeout_s
        self.on_disconnect = on_disconnect
        self.on_reconnect = on_reconnect
        self.on_state_change = on_state_change

        self._state = ConnectionState.DISCONNECTED
        self._last_message_time: Optional[float] = None
        self._monitor_task: Optional[asyncio.Task] = None

        # Statistics
        self._stats = ConnectionStats()

        # Event history (bounded)
        self._event_history: List[ConnectionEvent] = []
        self._max_history = 100

    def _transition_to(self, new_state: ConnectionState, reason: str = "") -> None:
        """
        Transition to a new state and emit events.

        Args:
            new_state: Target state
            reason: Optional reason for the transition
        """
        if new_state == self._state:
            return

        old_state = self._state
        now = time.monotonic()

        # Track downtime
        if old_state == ConnectionState.CONNECTED and new_state in (
            ConnectionState.RECONNECTING,
            ConnectionState.DISCONNECTED,
        ):
            self._stats.last_disconnect_time = now

        if (
            new_state == ConnectionState.CONNECTED
            and self._stats.last_disconnect_time is not None
        ):
            self._stats.total_downtime_s += now - self._stats.last_disconnect_time
            self._stats.last_disconnect_time = None

        # Create event
        event = ConnectionEvent(
            timestamp=now,
            from_state=old_state,
            to_state=new_state,
            reason=reason,
        )

        # Update state
        self._state = new_state

        # Record history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Update stats
        if new_state == ConnectionState.RECONNECTING:
            self._stats.disconnects += 1
        elif (
            new_state == ConnectionState.CONNECTED
            and old_state == ConnectionState.RECONNECTING
        ):
            self._stats.reconnects += 1

        # Fire callbacks
        if self.on_state_change:
            try:
                self.on_state_change(event)
            except Exception:
                pass

        # Legacy callbacks for backward compatibility
        if (
            old_state == ConnectionState.CONNECTED
            and new_state == ConnectionState.RECONNECTING
        ):
            if self.on_disconnect:
                try:
                    self.on_disconnect()
                except Exception:
                    pass
        elif new_state == ConnectionState.CONNECTED and old_state in (
            ConnectionState.RECONNECTING,
            ConnectionState.CONNECTING,
            ConnectionState.DISCONNECTED,
        ):
            # Fire on_reconnect for any transition TO connected state
            # (including first connection, for backward compatibility)
            if self.on_reconnect:
                try:
                    self.on_reconnect()
                except Exception:
                    pass

    def on_message_received(self) -> None:
        """Call this whenever any valid message arrives from firmware."""
        self._last_message_time = time.monotonic()
        self._stats.messages_received += 1

        if self._state == ConnectionState.CONNECTING:
            self._transition_to(ConnectionState.CONNECTED, "first_message")
        elif self._state == ConnectionState.RECONNECTING:
            self._transition_to(ConnectionState.CONNECTED, "message_after_timeout")
        elif self._state == ConnectionState.DISCONNECTED:
            # Received message while disconnected - transition through connecting
            self._state = ConnectionState.CONNECTING
            self._transition_to(ConnectionState.CONNECTED, "unexpected_message")

    def check(self) -> None:
        """Check for timeout. Call periodically or use start_monitoring()."""
        if self._last_message_time is None:
            return

        elapsed = time.monotonic() - self._last_message_time

        if self._state == ConnectionState.CONNECTED and elapsed > self.timeout_s:
            self._transition_to(
                ConnectionState.RECONNECTING, f"timeout_{elapsed:.2f}s"
            )

    async def start_monitoring(self, interval_s: float = 0.1) -> None:
        """Start background monitoring task and enter CONNECTING state."""
        if self._state == ConnectionState.DISCONNECTED:
            self._transition_to(ConnectionState.CONNECTING, "start_monitoring")

        self._monitor_task = asyncio.create_task(self._monitor_loop(interval_s))

    async def stop_monitoring(self) -> None:
        """Stop background monitoring task."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def _monitor_loop(self, interval_s: float) -> None:
        while True:
            self.check()
            await asyncio.sleep(interval_s)

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def connected(self) -> bool:
        """Check if connection is active (CONNECTED state)."""
        return self._state == ConnectionState.CONNECTED

    @property
    def time_since_last_message(self) -> Optional[float]:
        """Get time since last message, or None if no messages received."""
        if self._last_message_time is None:
            return None
        return time.monotonic() - self._last_message_time

    def get_stats(self) -> ConnectionStats:
        """Get connection statistics."""
        return self._stats

    def get_event_history(self, count: Optional[int] = None) -> List[ConnectionEvent]:
        """
        Get recent connection events.

        Args:
            count: Number of events to return (None = all)

        Returns:
            List of ConnectionEvent (oldest first)
        """
        if count is None:
            return list(self._event_history)
        return list(self._event_history[-count:])

    def reset(self) -> None:
        """Reset state (e.g., on manual disconnect)."""
        if self._state != ConnectionState.DISCONNECTED:
            self._transition_to(ConnectionState.DISCONNECTED, "manual_reset")
        self._last_message_time = None