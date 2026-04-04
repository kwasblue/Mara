# mara_host/observability/recording.py
"""
Observability recording infrastructure.

Promoted from research/recording.py with typed ObservableEvent support
and MCU/host timestamp correlation.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from .events import EventLayer, EventType, ObservableEvent

if TYPE_CHECKING:
    from mara_host.core.event_bus import EventBus
    from mara_host.logger.logger import MaraLogBundle

logger = logging.getLogger(__name__)


@dataclass
class RecordingConfig:
    """Configuration for recording sessions."""

    name: str
    log_dir: str = "logs"
    console: bool = False


class ObservabilityBus:
    """
    Central observability bus for cross-layer event tracking.

    Promoted from RecordingEventBus with:
    - Typed ObservableEvent schema
    - MCU/host timestamp correlation
    - Optional persistence to MaraLogBundle
    - Event handler subscriptions

    Example usage:
        obs = ObservabilityBus(log_bundle=bundle)
        obs.set_mcu_sync(mcu_uptime_ms)  # At handshake

        # Emit typed events
        obs.emit(ObservableEvent(...))

        # Or use convenience methods
        obs.emit_metric(EventLayer.HOST, "commander", {"latency_ms": 12.5})
    """

    def __init__(
        self,
        inner_bus: EventBus | None = None,
        log_bundle: MaraLogBundle | None = None,
        bundle: MaraLogBundle | None = None,  # Backwards compatibility alias
    ):
        """
        Initialize observability bus.

        Args:
            inner_bus: Optional EventBus to wrap (for publish forwarding).
            log_bundle: Optional MaraLogBundle for persistence.
            bundle: Deprecated alias for log_bundle (backwards compatibility).
        """
        self._bus = inner_bus
        # Support both log_bundle and bundle for backwards compatibility
        self._bundle = log_bundle if log_bundle is not None else bundle
        self._handlers: list[Callable[[ObservableEvent], None]] = []
        self._mcu_epoch_offset_ms: int = 0

    def set_mcu_sync(self, mcu_uptime_ms: int) -> None:
        """
        Synchronize MCU/host clocks at handshake.

        Call this at connection handshake with the MCU's reported uptime.
        All subsequent events can then correlate mcu_ts_ms with host_ts_ms.

        Args:
            mcu_uptime_ms: MCU uptime in milliseconds from handshake response.
        """
        self._mcu_epoch_offset_ms = int(time.time() * 1000) - mcu_uptime_ms
        logger.debug(
            "MCU clock sync: offset=%dms (host - mcu)",
            self._mcu_epoch_offset_ms,
        )

    def mcu_to_host_ts(self, mcu_ts_ms: int) -> int:
        """
        Convert MCU timestamp to host wall clock.

        Args:
            mcu_ts_ms: MCU uptime in milliseconds.

        Returns:
            Estimated host wall clock time in milliseconds.
        """
        return mcu_ts_ms + self._mcu_epoch_offset_ms

    def on_event(self, handler: Callable[[ObservableEvent], None]) -> None:
        """Subscribe to all observable events."""
        self._handlers.append(handler)

    def off_event(self, handler: Callable[[ObservableEvent], None]) -> None:
        """Unsubscribe from observable events."""
        try:
            self._handlers.remove(handler)
        except ValueError:
            pass

    def emit(self, event: ObservableEvent) -> None:
        """
        Emit an observable event.

        Persists to log bundle (if configured) and notifies all handlers.
        """
        # Persist to bundle if available
        if self._bundle is not None:
            try:
                self._bundle.events.write("observable", **event.to_dict())
            except Exception as e:
                logger.warning("Failed to persist event: %s", e)

        # Notify handlers
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning("Event handler error: %s", e)

    def emit_measurement(
        self,
        layer: EventLayer | str,
        source: str,
        value: float,
        mcu_ts_ms: int | None = None,
        **metadata: Any,
    ) -> None:
        """Convenience method for measurement events."""
        self.emit(
            ObservableEvent(
                mcu_ts_ms=mcu_ts_ms,
                host_ts_ms=int(time.time() * 1000),
                layer=layer,
                source=source,
                event_type=EventType.MEASUREMENT,
                value=value,
                metadata=metadata if metadata else None,
            )
        )

    def emit_metric(
        self,
        layer: EventLayer | str,
        source: str,
        values: dict[str, float],
        **metadata: Any,
    ) -> None:
        """Convenience method for metric events."""
        self.emit(
            ObservableEvent(
                mcu_ts_ms=None,
                host_ts_ms=int(time.time() * 1000),
                layer=layer,
                source=source,
                event_type=EventType.METRIC,
                values=values,
                metadata=metadata if metadata else None,
            )
        )

    def emit_state_change(
        self,
        layer: EventLayer | str,
        source: str,
        state: str,
        mcu_ts_ms: int | None = None,
        **metadata: Any,
    ) -> None:
        """Convenience method for state change events."""
        self.emit(
            ObservableEvent(
                mcu_ts_ms=mcu_ts_ms,
                host_ts_ms=int(time.time() * 1000),
                layer=layer,
                source=source,
                event_type=EventType.STATE_CHANGE,
                state=state,
                metadata=metadata if metadata else None,
            )
        )

    def emit_error(
        self,
        layer: EventLayer | str,
        source: str,
        error: str,
        **metadata: Any,
    ) -> None:
        """Convenience method for error events."""
        self.emit(
            ObservableEvent(
                mcu_ts_ms=None,
                host_ts_ms=int(time.time() * 1000),
                layer=layer,
                source=source,
                event_type=EventType.ERROR,
                error=error,
                metadata=metadata if metadata else None,
            )
        )

    # EventBus compatibility methods (for wrapping existing bus)
    def bus_subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        """Forward subscribe to inner bus."""
        if self._bus is not None:
            self._bus.subscribe(topic, handler)

    def bus_publish(self, topic: str, data: Any) -> None:
        """
        Forward publish to inner bus and log as observable event.

        Use this when wrapping an existing EventBus to record all publishes.
        """
        if self._bundle is not None:
            self._bundle.events.write(
                "bus.publish",
                topic=topic,
                data=data,
            )
        if self._bus is not None:
            self._bus.publish(topic, data)

    # Backwards compatibility aliases for RecordingEventBus API
    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        """Backwards compatible alias for bus_subscribe."""
        self.bus_subscribe(topic, handler)

    def publish(self, topic: str, data: Any) -> None:
        """Backwards compatible alias for bus_publish."""
        self.bus_publish(topic, data)


# Legacy alias for backwards compatibility
RecordingEventBus = ObservabilityBus


class RecordingTransport:
    """
    Wraps any transport to record rx/tx frames.

    Works with the transport interface:
      - set_frame_handler(handler)
      - start(), stop()
      - send_frame(...) or _send_bytes(...)

    Example:
        wrapped = RecordingTransport(serial_transport, bundle)
        client.set_transport(wrapped)
    """

    def __init__(self, inner_transport: Any, bundle: MaraLogBundle):
        self._t = inner_transport
        self._bundle = bundle

    def set_frame_handler(self, handler: Callable[[bytes], None]) -> None:
        """Wrap frame handler to record received frames."""

        def wrapped(body: bytes) -> None:
            self._bundle.events.write("transport.rx", n=len(body), body=body)
            handler(body)

        self._t.set_frame_handler(wrapped)

    def start(self) -> Any:
        """Start transport and log."""
        self._bundle.events.write("transport.start", type=type(self._t).__name__)
        return self._t.start()

    def stop(self) -> Any:
        """Stop transport and log."""
        self._bundle.events.write("transport.stop", type=type(self._t).__name__)
        return self._t.stop()

    def send_frame(self, msg_type: int, payload: bytes) -> Any:
        """Send frame and log."""
        self._bundle.events.write(
            "transport.tx", msg_type=msg_type, n=len(payload), payload=payload
        )
        return self._t.send_frame(msg_type, payload)

    def _send_bytes(self, data: bytes) -> Any:
        """Send raw bytes and log."""
        self._bundle.events.write("transport.tx.raw", n=len(data), data=data)
        return self._t._send_bytes(data)

    def __getattr__(self, name: str) -> Any:
        """Forward other attributes to inner transport."""
        return getattr(self._t, name)
