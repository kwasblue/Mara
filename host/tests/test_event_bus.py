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
