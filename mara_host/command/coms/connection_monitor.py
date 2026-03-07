# mara_host/core/connection_monitor.py

import asyncio
import time
from typing import Optional, Callable


class ConnectionMonitor:
    """
    Monitors connection health based on incoming messages.
    
    Integrates with your EventBus - subscribe to messages and call on_message_received().
    """
    
    def __init__(
        self,
        timeout_s: float = 1.0,
        on_disconnect: Optional[Callable[[], None]] = None,
        on_reconnect: Optional[Callable[[], None]] = None,
    ):
        self.timeout_s = timeout_s
        self.on_disconnect = on_disconnect
        self.on_reconnect = on_reconnect
        
        self._last_message_time: Optional[float] = None
        self._connected = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    def on_message_received(self) -> None:
        """Call this whenever any valid message arrives from firmware."""
        was_connected = self._connected
        self._last_message_time = time.monotonic()
        self._connected = True
        
        if not was_connected and self.on_reconnect:
            self.on_reconnect()
    
    def check(self) -> None:
        """Check for timeout. Call periodically or use start_monitoring()."""
        if self._last_message_time is None:
            return
        
        elapsed = time.monotonic() - self._last_message_time
        
        if self._connected and elapsed > self.timeout_s:
            self._connected = False
            if self.on_disconnect:
                self.on_disconnect()
    
    async def start_monitoring(self, interval_s: float = 0.1) -> None:
        """Start background monitoring task."""
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
    def connected(self) -> bool:
        return self._connected
    
    @property
    def time_since_last_message(self) -> Optional[float]:
        if self._last_message_time is None:
            return None
        return time.monotonic() - self._last_message_time
    
    def reset(self) -> None:
        """Reset state (e.g., on manual disconnect)."""
        self._last_message_time = None
        self._connected = False