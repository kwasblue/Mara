# mara_host/research/recording.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
from mara_host.logger.logger import MaraLogBundle
from mara_host.core.event_bus import EventBus


@dataclass
class RecordingConfig:
    name: str
    log_dir: str = "logs"
    console: bool = False


class RecordingEventBus:
    """Wraps EventBus; records publish()."""
    def __init__(self, inner_bus: EventBus, bundle: MaraLogBundle):
        self._bus = inner_bus
        self._bundle = bundle

    def subscribe(self, topic: str, handler: Callable[[Any], None]):
        return self._bus.subscribe(topic, handler)

    def publish(self, topic: str, data: Any):
        self._bundle.events.write(
            "bus.publish",
            topic=topic,
            data=data,
        )
        return self._bus.publish(topic, data)


class RecordingTransport:
    """
    Wraps any transport; records rx/tx bodies.
    Works with your transport interface:
      - set_frame_handler(handler)
      - start(), stop()
      - and either send_frame(...) or _send_bytes(...)
    """
    def __init__(self, inner_transport, bundle: MaraLogBundle):
        self._t = inner_transport
        self._bundle = bundle

    def set_frame_handler(self, handler):
        def wrapped(body: bytes):
            self._bundle.events.write("transport.rx", n=len(body), body=body)
            handler(body)
        self._t.set_frame_handler(wrapped)

    def start(self):
        self._bundle.events.write("transport.start", type=type(self._t).__name__)
        return self._t.start()

    def stop(self):
        self._bundle.events.write("transport.stop", type=type(self._t).__name__)
        return self._t.stop()

    # If the inner transport exposes send_frame (BaseTransport does), wrap it:
    def send_frame(self, msg_type: int, payload: bytes):
        self._bundle.events.write("transport.tx", msg_type=msg_type, n=len(payload), payload=payload)
        return self._t.send_frame(msg_type, payload)

    # If some transport only has send_bytes, you can optionally support it:
    def _send_bytes(self, data: bytes):
        self._bundle.events.write("transport.tx.raw", n=len(data), data=data)
        return self._t._send_bytes(data)
