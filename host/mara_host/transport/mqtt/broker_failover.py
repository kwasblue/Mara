# mara_host/mqtt/broker_failover.py
"""
MQTT broker failover logic.

Handles automatic failover between primary and fallback brokers.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

import aiomqtt


class BrokerState(Enum):
    """Current broker connection state."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILING = "failing"


@dataclass
class BrokerConfig:
    """Configuration for a broker endpoint."""
    host: str
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    name: str = "broker"


class BrokerFailover:
    """
    Manages failover between primary and fallback MQTT brokers.

    Logic:
    1. Monitor primary broker connection
    2. On disconnect: attempt reconnect with exponential backoff
    3. After N failures: switch to fallback broker
    4. Periodically check if primary is back, switch when available
    """

    def __init__(
        self,
        primary: BrokerConfig,
        fallback: Optional[BrokerConfig] = None,
        max_retries: int = 3,
        base_delay_s: float = 1.0,
        max_delay_s: float = 30.0,
        primary_check_interval_s: float = 60.0,
        on_broker_change: Optional[Callable[[BrokerConfig], None]] = None,
        on_state_change: Optional[Callable[[BrokerState], None]] = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._max_retries = max_retries
        self._base_delay_s = base_delay_s
        self._max_delay_s = max_delay_s
        self._primary_check_interval_s = primary_check_interval_s

        self._on_broker_change = on_broker_change
        self._on_state_change = on_state_change

        # State
        self._current_broker = primary
        self._state = BrokerState.DISCONNECTED
        self._retry_count = 0
        self._using_fallback = False
        self._last_primary_check = 0.0

        # Tasks
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_broker(self) -> BrokerConfig:
        """Get the currently active broker config."""
        return self._current_broker

    @property
    def state(self) -> BrokerState:
        """Get current connection state."""
        return self._state

    @property
    def is_using_fallback(self) -> bool:
        """Check if currently using fallback broker."""
        return self._using_fallback

    @property
    def retry_count(self) -> int:
        """Get current retry count."""
        return self._retry_count

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start failover monitoring."""
        if self._monitor_task is not None:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop failover monitoring."""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    def notify_connected(self) -> None:
        """Notify that connection succeeded."""
        self._set_state(BrokerState.CONNECTED)
        self._retry_count = 0

    def notify_disconnected(self) -> None:
        """Notify that connection was lost."""
        self._set_state(BrokerState.DISCONNECTED)

    def notify_connection_failed(self) -> None:
        """Notify that a connection attempt failed."""
        self._retry_count += 1
        self._set_state(BrokerState.FAILING)

    async def get_next_broker(self) -> tuple[BrokerConfig, float]:
        """
        Get the next broker to try and delay before connecting.

        Returns:
            (broker_config, delay_seconds)
        """
        # Check if we should switch to fallback
        if self._retry_count >= self._max_retries and self._fallback and not self._using_fallback:
            print(f"[BrokerFailover] Switching to fallback broker: {self._fallback.name}")
            self._current_broker = self._fallback
            self._using_fallback = True
            self._retry_count = 0

            if self._on_broker_change:
                self._on_broker_change(self._current_broker)

            return self._current_broker, 0.0

        # Calculate delay with exponential backoff
        if self._retry_count > 0:
            delay = min(
                self._base_delay_s * (2 ** (self._retry_count - 1)),
                self._max_delay_s,
            )
        else:
            delay = 0.0

        return self._current_broker, delay

    async def check_primary_available(self) -> bool:
        """
        Check if primary broker is available.

        Used when on fallback to determine if we can switch back.
        """
        if not self._using_fallback:
            return True

        try:
            async with aiomqtt.Client(
                hostname=self._primary.host,
                port=self._primary.port,
                username=self._primary.username,
                password=self._primary.password,
                identifier="health-check",
                clean_session=True,
            ) as client:
                # Successfully connected
                return True
        except Exception:
            return False

    async def switch_to_primary(self) -> bool:
        """
        Switch back to primary broker.

        Returns True if switch was initiated.
        """
        if not self._using_fallback:
            return False

        if await self.check_primary_available():
            print(f"[BrokerFailover] Switching back to primary broker: {self._primary.name}")
            self._current_broker = self._primary
            self._using_fallback = False
            self._retry_count = 0

            if self._on_broker_change:
                self._on_broker_change(self._current_broker)

            return True

        return False

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------

    def _set_state(self, state: BrokerState) -> None:
        """Update state and notify callback."""
        if self._state != state:
            self._state = state
            if self._on_state_change:
                self._on_state_change(state)

    async def _monitor_loop(self) -> None:
        """Background task to check primary availability."""
        while self._running:
            try:
                await asyncio.sleep(self._primary_check_interval_s)

                if self._using_fallback:
                    now = time.time()
                    if now - self._last_primary_check >= self._primary_check_interval_s:
                        self._last_primary_check = now
                        await self.switch_to_primary()

            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[BrokerFailover] Monitor error: {e}")
