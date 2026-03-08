from dataclasses import dataclass
from typing import Callable, Optional, Any

from mara_host.core import protocol


def _decode_frames_from_bytes(blob: bytes) -> list[bytes]:
    """
    Uses host protocol.extract_frames to decode one or more frames from bytes.
    Returns list of bodies: body[0]=msg_type, body[1:]=payload
    """
    buf = bytearray(blob)
    bodies: list[bytes] = []
    protocol.extract_frames(buf, lambda body: bodies.append(body))
    return bodies


@dataclass
class PublishedEvent:
    topic: str
    data: Any


class CapturingBus:
    """
    Wraps your EventBus-like interface: publish(topic, data).
    Useful for asserting what got published.
    """
    def __init__(self) -> None:
        self.events: list[PublishedEvent] = []
        self.subscribers: dict[str, list[Callable[[Any], None]]] = {}

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        self.subscribers.setdefault(topic, []).append(handler)

    def publish(self, topic: str, data: Any) -> None:
        self.events.append(PublishedEvent(topic, data))
        for h in self.subscribers.get(topic, []):
            h(data)

    def topics(self) -> list[str]:
        return [e.topic for e in self.events]

    def last(self, topic: str) -> Optional[PublishedEvent]:
        for e in reversed(self.events):
            if e.topic == topic:
                return e
        return None


