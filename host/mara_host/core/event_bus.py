# mara_host/core/event_bus.py

from collections import defaultdict
from typing import Callable, Dict, List, Any


class EventBus:
    """
    Simple synchronous event bus.
    Works fine when called from async code; just make sure handlers are fast.
    """

    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        """Register a handler for a topic."""
        self._subs[topic].append(handler)

    def publish(self, topic: str, data: Any) -> None:
        """Call all handlers for a topic."""
        for h in self._subs.get(topic, []):
            try:
                h(data)
            except Exception as e:  # don't kill the loop if one handler dies
                print(f"[Bus] handler error on '{topic}': {e}")
