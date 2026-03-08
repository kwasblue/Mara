# mara_host/core/event_bus.py

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Any, Union, Coroutine

logger = logging.getLogger(__name__)

# Type alias for handlers (sync or async)
Handler = Callable[[Any], Union[None, Coroutine[Any, Any, None]]]


class EventBus:
    """
    Event bus supporting both synchronous and asynchronous handlers.

    - publish(): Synchronous dispatch (fast, for sync handlers)
    - publish_async(): Async dispatch (awaits async handlers without blocking)

    Works fine when called from async code; just make sure sync handlers are fast.
    """

    def __init__(self) -> None:
        self._subs: Dict[str, List[Handler]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Handler) -> None:
        """Register a handler for a topic (sync or async)."""
        self._subs[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        """Remove a handler from a topic."""
        if topic in self._subs:
            try:
                self._subs[topic].remove(handler)
            except ValueError:
                pass  # Handler not found, ignore

    def publish(self, topic: str, data: Any) -> None:
        """
        Call all handlers for a topic (synchronous).

        For best performance, ensure handlers are fast.
        Async handlers will NOT be awaited - use publish_async() for those.
        """
        for h in self._subs.get(topic, []):
            try:
                result = h(data)
                # If handler returns a coroutine, we can't await it here
                # Log a warning - user should use publish_async instead
                if asyncio.iscoroutine(result):
                    result.close()  # Clean up unawaited coroutine
                    logger.warning(
                        "Async handler on '%s' called via publish(). "
                        "Use publish_async() for async handlers.",
                        topic,
                    )
            except Exception as e:  # don't kill the loop if one handler dies
                logger.warning("Handler error on '%s': %s", topic, e)

    async def publish_async(self, topic: str, data: Any) -> None:
        """
        Call all handlers for a topic with async support.

        Async handlers are awaited; sync handlers are called directly.
        Use this when you have async handlers or when calling from async context.
        """
        handlers = self._subs.get(topic, [])
        for h in handlers:
            try:
                if asyncio.iscoroutinefunction(h):
                    await h(data)
                else:
                    h(data)
            except Exception as e:
                logger.warning("Handler error on '%s': %s", topic, e)
