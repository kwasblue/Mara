# mara_host/core/event_bus.py

import logging
from collections import defaultdict
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)


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

    def unsubscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        """Remove a handler from a topic."""
        if topic in self._subs:
            try:
                self._subs[topic].remove(handler)
            except ValueError:
                pass  # Handler not found, ignore

    def publish(self, topic: str, data: Any) -> None:
        """Call all handlers for a topic."""
        for h in self._subs.get(topic, []):
            try:
                h(data)
            except Exception as e:  # don't kill the loop if one handler dies
                logger.warning("Handler error on '%s': %s", topic, e)
