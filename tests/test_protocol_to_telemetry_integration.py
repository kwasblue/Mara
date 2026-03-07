# tests/test_client_telemetry_bin_routing.py
import asyncio
import pytest
import struct

from mara_host.command.client import BaseAsyncRobotClient
from mara_host.core import protocol
from tests.helpers import CapturingBus
from tests.fakes.fake_async_transport import FakeAsyncTransport

SECTION_IMU = 1


def _build_sectioned_payload(ts_ms: int = 1234, seq: int = 7) -> bytes:
    version = 1

    # 2x u8 + 7x i16 = 9 items
    imu_bytes = struct.pack(
        "<BBhhhhhhh",
        1,  # online
        1,  # ok
        1000,   # ax_mg
        -500,   # ay_mg
        0,      # az_mg
        250,    # gx_mdps
        -250,   # gy_mdps
        0,      # gz_mdps
        2500,   # temp_c_centi
    )

    payload = bytearray()
    payload += struct.pack("<BHI", version, seq & 0xFFFF, ts_ms & 0xFFFFFFFF)
    payload += struct.pack("<B", 1)  # section_count
    payload += struct.pack("<BH", SECTION_IMU, len(imu_bytes))
    payload += imu_bytes
    return bytes(payload)


@pytest.mark.asyncio
async def test_client_routes_telemetry_bin_to_packet_topic():
    bus = CapturingBus()
    transport = FakeAsyncTransport()
    client = BaseAsyncRobotClient(transport=transport, bus=bus, require_version_match=False)

    await client.start()
    try:
        telem_payload = _build_sectioned_payload(ts_ms=1234, seq=7)

        # body = [msg_type][payload...]
        body = bytes([protocol.MSG_TELEMETRY_BIN]) + telem_payload
        transport._inject_body(body)

        # if bus delivery is deferred, yield once
        await asyncio.sleep(0)

        # ✅ client publishes telemetry.binary (not telemetry.packet)
        evt = bus.last("telemetry.binary")
        assert evt is not None, "Expected telemetry.binary publication for MSG_TELEMETRY_BIN"

        packet = getattr(evt, "data", evt)
        assert packet.ts_ms == 1234
        assert packet.imu is not None
        assert packet.imu.online is True

    finally:
        await client.stop()
