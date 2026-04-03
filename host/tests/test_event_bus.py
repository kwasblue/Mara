import asyncio
import pytest
from unittest.mock import MagicMock, patch
from mara_host.core.event_bus import EventBus


def test_event_bus_subscribe_publish():
    bus = EventBus()
    got = []

    def handler(data):
        got.append(data)

    bus.subscribe("t", handler)
    bus.publish("t", {"a": 1})
    bus.publish("t", {"b": 2})

    assert got == [{"a": 1}, {"b": 2}]


def test_unsubscribe_removes_handler():
    bus = EventBus()
    got = []

    def handler(data):
        got.append(data)

    bus.subscribe("topic", handler)
    bus.publish("topic", 1)
    bus.unsubscribe("topic", handler)
    bus.publish("topic", 2)

    assert got == [1]  # Only first publish received


def test_unsubscribe_during_callback():
    """Verify handler list mutation during iteration doesn't skip handlers.

    This tests the fix where publish() iterates over a snapshot copy
    instead of the live handlers list.
    """
    bus = EventBus()
    results = []

    def handler1(data):
        results.append("h1")
        # Unsubscribe self during callback - this used to skip handler2
        bus.unsubscribe("topic", handler1)

    def handler2(data):
        results.append("h2")

    def handler3(data):
        results.append("h3")

    bus.subscribe("topic", handler1)
    bus.subscribe("topic", handler2)
    bus.subscribe("topic", handler3)

    bus.publish("topic", {})

    # All three handlers should have been called despite h1 unsubscribing
    assert results == ["h1", "h2", "h3"]

    # h1 is now unsubscribed, only h2 and h3 should fire
    results.clear()
    bus.publish("topic", {})
    assert results == ["h2", "h3"]


def test_unsubscribe_other_handler_during_callback():
    """Verify unsubscribing a different handler during callback works."""
    bus = EventBus()
    results = []

    def handler2(data):
        results.append("h2")

    def handler1(data):
        results.append("h1")
        # Unsubscribe handler2 while iterating
        bus.unsubscribe("topic", handler2)

    bus.subscribe("topic", handler1)
    bus.subscribe("topic", handler2)

    bus.publish("topic", {})

    # Both should have been called (snapshot was taken before mutation)
    assert results == ["h1", "h2"]


@pytest.mark.asyncio
async def test_async_handler_multi_topic_partial_unsubscribe():
    """Verify async handler subscribed to multiple topics isn't prematurely removed.

    This tests the fix where _async_handlers only removes a handler when it
    has no remaining subscriptions on any topic.
    """
    bus = EventBus()
    results = []

    async def async_handler(data):
        results.append(data)

    # Subscribe same async handler to two topics
    bus.subscribe("topic1", async_handler)
    bus.subscribe("topic2", async_handler)

    # Handler should be tracked as async
    assert async_handler in bus._async_handlers

    # Unsubscribe from topic1 only
    bus.unsubscribe("topic1", async_handler)

    # Handler should still be tracked as async (still subscribed to topic2)
    assert async_handler in bus._async_handlers

    # Publish to topic2 should still work as async
    await bus.publish_async("topic2", "test")
    assert results == ["test"]

    # Now unsubscribe from topic2
    bus.unsubscribe("topic2", async_handler)

    # Handler should now be removed from async tracking
    assert async_handler not in bus._async_handlers


@pytest.mark.asyncio
async def test_publish_async_with_async_handlers():
    """Verify publish_async properly awaits async handlers."""
    bus = EventBus()
    results = []

    async def async_handler(data):
        await asyncio.sleep(0.01)  # Simulate async work
        results.append(f"async:{data}")

    def sync_handler(data):
        results.append(f"sync:{data}")

    bus.subscribe("topic", async_handler)
    bus.subscribe("topic", sync_handler)

    await bus.publish_async("topic", "test")

    # Both handlers should have run
    assert "async:test" in results
    assert "sync:test" in results


@pytest.mark.asyncio
async def test_publish_async_mutation_during_callback():
    """Verify publish_async also uses snapshot to prevent mutation issues."""
    bus = EventBus()
    results = []

    async def handler1(data):
        results.append("h1")
        bus.unsubscribe("topic", handler1)

    async def handler2(data):
        results.append("h2")

    bus.subscribe("topic", handler1)
    bus.subscribe("topic", handler2)

    await bus.publish_async("topic", {})

    assert results == ["h1", "h2"]


def test_publish_warns_on_async_handler():
    """Verify sync publish() warns when async handler is used."""
    bus = EventBus()

    async def async_handler(data):
        pass

    bus.subscribe("topic", async_handler)

    with patch("mara_host.core.event_bus.logger") as mock_logger:
        bus.publish("topic", {})
        # Should warn about async handler being called via sync publish
        mock_logger.warning.assert_called()
        call_args = str(mock_logger.warning.call_args)
        assert "publish_async" in call_args or "Async handler" in call_args


def test_subscription_leak_warning():
    """Verify warning is logged when subscription count exceeds threshold."""
    bus = EventBus()

    with patch("mara_host.core.event_bus.logger") as mock_logger:
        # Subscribe more handlers than the threshold
        for i in range(bus._SUBSCRIPTION_WARN_THRESHOLD + 1):
            bus.subscribe("topic", lambda d, i=i: None)

        # Should have warned about high subscription count
        mock_logger.warning.assert_called()
        call_args = str(mock_logger.warning.call_args)
        assert "subscription" in call_args.lower() or "High" in call_args


def test_get_subscription_count():
    """Verify get_subscription_count() returns accurate counts."""
    bus = EventBus()

    assert bus.get_subscription_count() == {}

    bus.subscribe("topic1", lambda d: None)
    bus.subscribe("topic1", lambda d: None)
    bus.subscribe("topic2", lambda d: None)

    counts = bus.get_subscription_count()
    assert counts["topic1"] == 2
    assert counts["topic2"] == 1


def test_get_subscription_count_excludes_empty():
    """Verify get_subscription_count() excludes topics with no handlers."""
    bus = EventBus()

    def handler(d):
        pass

    bus.subscribe("topic", handler)
    assert bus.get_subscription_count() == {"topic": 1}

    bus.unsubscribe("topic", handler)
    # Topic should not appear in counts after all handlers removed
    assert bus.get_subscription_count() == {}


def test_publish_to_nonexistent_topic():
    """Verify publish to nonexistent topic is a no-op."""
    bus = EventBus()
    # Should not raise
    bus.publish("nonexistent", {"data": 1})


def test_handler_exception_doesnt_stop_others():
    """Verify one handler's exception doesn't prevent other handlers from running."""
    bus = EventBus()
    results = []

    def bad_handler(data):
        raise ValueError("oops")

    def good_handler(data):
        results.append(data)

    bus.subscribe("topic", bad_handler)
    bus.subscribe("topic", good_handler)

    with patch("mara_host.core.event_bus.logger"):
        bus.publish("topic", "test")

    # Good handler should still have run despite bad handler's exception
    assert results == ["test"]


def test_unsubscribe_nonexistent_handler():
    """Verify unsubscribing a non-subscribed handler is a no-op."""
    bus = EventBus()

    def handler1(d):
        pass

    def handler2(d):
        pass

    bus.subscribe("topic", handler1)
    # Should not raise
    bus.unsubscribe("topic", handler2)

    # handler1 should still be subscribed
    assert bus.get_subscription_count() == {"topic": 1}


def test_unsubscribe_from_nonexistent_topic():
    """Verify unsubscribing from nonexistent topic is a no-op."""
    bus = EventBus()

    def handler(d):
        pass

    # Should not raise
    bus.unsubscribe("nonexistent", handler)
