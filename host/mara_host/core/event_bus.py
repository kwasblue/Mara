# mara_host/core/event_bus.py

import asyncio
import inspect
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Any, Union, Coroutine, Set

logger = logging.getLogger(__name__)

# Type alias for handlers (sync or async)
Handler = Callable[[Any], Union[None, Coroutine[Any, Any, None]]]


class EventBus:
    """
    Event bus supporting both synchronous and asynchronous handlers.

    - publish(): Synchronous dispatch (fast, for sync handlers)
    - publish_async(): Async dispatch (awaits async handlers without blocking)

    Works fine when called from async code; just make sure sync handlers are fast.

    Optimization: Tracks async handlers separately to avoid iscoroutine() check
    on hot path when all handlers are synchronous (common case for telemetry).
    """

    def __init__(self) -> None:
        self._subs: Dict[str, List[Handler]] = defaultdict(list)
        # Track async handlers separately to enable fast-path for sync-only topics
        self._async_handlers: Set[Handler] = set()

    # Threshold for subscription leak warning
    _SUBSCRIPTION_WARN_THRESHOLD = 10

    def subscribe(self, topic: str, handler: Handler) -> None:
        """Register a handler for a topic (sync or async)."""
        self._subs[topic].append(handler)
        # Track async handlers at subscription time (avoids check on every publish)
        if inspect.iscoroutinefunction(handler):
            self._async_handlers.add(handler)
        # Warn on suspicious subscription counts (possible leak)
        count = len(self._subs[topic])
        if count > self._SUBSCRIPTION_WARN_THRESHOLD:
            logger.warning(
                "High subscription count on '%s': %d handlers (possible leak?)",
                topic,
                count,
            )

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        """Remove a handler from a topic."""
        if topic in self._subs:
            try:
                self._subs[topic].remove(handler)
                # Clean up async handler tracking
                self._async_handlers.discard(handler)
            except ValueError:
                pass  # Handler not found, ignore

    def publish(self, topic: str, data: Any) -> None:
        """
        Call all handlers for a topic (synchronous).

        For best performance, ensure handlers are fast.
        Async handlers will NOT be awaited - use publish_async() for those.

        Optimized: Only checks for coroutine result if handler is known to be async.
        """
        handlers = self._subs.get(topic)
        if not handlers:
            return

        # Fast path: check if any async handlers exist for this topic
        async_handlers = self._async_handlers
        has_async = any(h in async_handlers for h in handlers)

        if not has_async:
            # Ultra-fast path: all handlers are sync, no coroutine checks needed
            for h in handlers:
                try:
                    h(data)
                except Exception as e:
                    logger.warning("Handler error on '%s': %s", topic, e)
        else:
            # Slower path: mixed sync/async handlers
            for h in handlers:
                try:
                    result = h(data)
                    # Only check for coroutine if handler is known async
                    if h in async_handlers and asyncio.iscoroutine(result):
                        result.close()  # Clean up unawaited coroutine
                        logger.warning(
                            "Async handler on '%s' called via publish(). "
                            "Use publish_async() for async handlers.",
                            topic,
                        )
                except Exception as e:
                    logger.warning("Handler error on '%s': %s", topic, e)

    async def publish_async(self, topic: str, data: Any) -> None:
        """
        Call all handlers for a topic with async support.

        Async handlers are awaited; sync handlers are called directly.
        Use this when you have async handlers or when calling from async context.

        Optimized: Uses pre-tracked async handler set instead of iscoroutinefunction() check.
        """
        handlers = self._subs.get(topic)
        if not handlers:
            return

        async_handlers = self._async_handlers
        for h in handlers:
            try:
                if h in async_handlers:
                    await h(data)
                else:
                    h(data)
            except Exception as e:
                logger.warning("Handler error on '%s': %s", topic, e)

    def get_subscription_count(self) -> Dict[str, int]:
        """
        Get count of subscriptions per topic.

        Useful for debugging subscription leaks after disconnect.

        Returns:
            Dict mapping topic names to handler counts (only non-empty topics)
        """
        return {
            topic: len(handlers)
            for topic, handlers in self._subs.items()
            if handlers
        }
