# tests/test_client_telemetry_bin_routing.py
import asyncio
import pytest
import struct

from mara_host.command.client import BaseMaraClient
from mara_host.core import protocol
from tests.helpers import CapturingBus
from tests.fakes.fake_async_transport import FakeAsyncTransport

SECTION_IMU = 1

def _build_sectioned_payload(ts_ms: int = 1234, seq: int = 7) -> bytes:
    """
    Telemetry BIN format:
      u8  version (=1)
      u16 seq
      u32 ts_ms
      u8  section_count
      repeat:
        u8  section_id
        u16 section_len
        u8[] section_bytes

    IMU section bytes:
      online(u8), ok(u8),
      ax_mg(i16), ay_mg(i16), az_mg(i16),
      gx_mdps(i16), gy_mdps(i16), gz_mdps(i16),
      temp_c_centi(i16)
    """
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
    client = BaseMaraClient(
        transport=transport,
        bus=bus,
        require_version_match=False,
    )

    await client.start()
    try:
        telem_payload = _build_sectioned_payload(ts_ms=1234, seq=7)

        # _on_frame expects body = [msg_type][payload...]
        body = bytes([protocol.MSG_TELEMETRY_BIN]) + telem_payload
        transport._inject_body(body)

        # allow loop callbacks to run
        await asyncio.sleep(0)

        # ✅ client publishes telemetry.binary
        evt = bus.last("telemetry.binary")
        assert evt is not None, "Expected telemetry.binary publication for MSG_TELEMETRY_BIN"

        packet = evt.data
        assert packet.ts_ms == 1234
        assert packet.imu is not None
        assert packet.imu.online is True
    finally:
        await client.stop()
