import json

from robot_host.command.client import BaseAsyncRobotClient
from robot_host.core import protocol
from tests.helpers import CapturingBus
from tests.fakes.fake_async_transport import FakeAsyncTransport


def test_client_json_telemetry_still_publishes_topics():
    bus = CapturingBus()
    transport = FakeAsyncTransport()
    client = BaseAsyncRobotClient(transport=transport, bus=bus, require_version_match=False)

    msg = {"src": "mcu", "type": "TELEMETRY", "ts_ms": 999, "data": {"imu": {"online": True, "ok": True}}}
    payload = json.dumps(msg).encode("utf-8")

    body = bytes([protocol.MSG_CMD_JSON]) + payload
    transport._inject_body(body)

    assert bus.last("telemetry.raw") is not None
    assert bus.last("telemetry") is not None
