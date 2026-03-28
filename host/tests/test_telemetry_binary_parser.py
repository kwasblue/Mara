import struct

from mara_host.telemetry.binary_parser import (
    parse_telemetry_bin,
    TELEM_IMU,
    TELEM_ULTRASONIC,
    TELEM_ENCODER0,
    TELEM_SENSOR_HEALTH,
)

def build_sectioned_packet(ts_ms: int, seq: int, sections: list[tuple[int, bytes]], ver: int = 1) -> bytes:
    # u8 ver, u16 seq, u32 ts_ms, u8 section_count
    out = bytearray()
    out += struct.pack("<BHIB", ver, seq, ts_ms, len(sections))
    for section_id, body in sections:
        out += struct.pack("<BH", section_id, len(body))
        out += body
    return bytes(out)

def test_bin_telem_imu_v1_parses():
    ts_ms = 123456
    seq = 7

    # IMU section: <BB7h> (online, ok, ax,ay,az,gx,gy,gz,temp)
    imu_body = struct.pack(
        "<BB7h",
        1, 1,
        100, -200, 300,      # mg
        400, -500, 600,      # mdps
        2500,                # centi-degC -> 25.00C
    )

    payload = build_sectioned_packet(ts_ms, seq, [(TELEM_IMU, imu_body)])
    pkt = parse_telemetry_bin(payload)

    assert pkt.ts_ms == ts_ms
    assert pkt.imu is not None
    assert pkt.imu.online is True
    assert pkt.imu.ok is True
    assert abs(pkt.imu.ax_g - 0.1) < 1e-6
    assert abs(pkt.imu.ay_g - (-0.2)) < 1e-6
    assert abs(pkt.imu.gz_dps - 0.6) < 1e-6
    assert abs(pkt.imu.temp_c - 25.0) < 1e-6

def test_bin_telem_ultrasonic_v1_parses():
    ts_ms = 42
    seq = 1

    # Ultrasonic section: <BBBH> (sensor_id, attached, ok, dist_mm)
    ultra_body = struct.pack("<BBBH", 2, 1, 1, 1234)  # 1234mm = 123.4cm
    payload = build_sectioned_packet(ts_ms, seq, [(TELEM_ULTRASONIC, ultra_body)])
    pkt = parse_telemetry_bin(payload)

    assert pkt.ultrasonic is not None
    assert pkt.ultrasonic.sensor_id == 2
    assert pkt.ultrasonic.attached is True
    assert pkt.ultrasonic.ok is True
    assert abs(pkt.ultrasonic.distance_cm - 123.4) < 1e-6

def test_bin_telem_multiple_sections():
    ts_ms = 999
    seq = 2

    imu_body = struct.pack("<BB7h", 1, 1, 0, 0, 0, 0, 0, 0, 0)
    enc_body = struct.pack("<i", -123)

    payload = build_sectioned_packet(ts_ms, seq, [(TELEM_IMU, imu_body), (TELEM_ENCODER0, enc_body)])
    pkt = parse_telemetry_bin(payload)

    assert pkt.imu is not None
    assert pkt.encoder0 is not None
    assert pkt.encoder0.ticks == -123

def test_bin_telem_sensor_health_parses():
    ts_ms = 314
    seq = 9

    # count=2, then (kind, sensor_id, flags, detail)*
    # imu healthy+present, ultrasonic present+degraded detail=2
    body = bytes([
        2,
        1, 0, 0x03, 0,
        2, 0, 0x05, 2,
    ])
    payload = build_sectioned_packet(ts_ms, seq, [(TELEM_SENSOR_HEALTH, body)])
    pkt = parse_telemetry_bin(payload)

    assert pkt.sensor_health is not None
    assert len(pkt.sensor_health.sensors) == 2
    imu = pkt.sensor_health.sensors[0]
    ultra = pkt.sensor_health.sensors[1]
    assert imu.kind == "imu"
    assert imu.present is True
    assert imu.healthy is True
    assert imu.degraded is False
    assert ultra.kind == "ultrasonic"
    assert ultra.present is True
    assert ultra.healthy is False
    assert ultra.degraded is True
    assert ultra.detail == 2


def test_bin_telem_unknown_section_is_ignored():
    ts_ms = 1
    seq = 0

    unknown_body = b"\x01\x02\x03"
    payload = build_sectioned_packet(ts_ms, seq, [(99, unknown_body)])
    pkt = parse_telemetry_bin(payload)

    # Should not crash; just return empty packet with timestamp
    assert pkt.ts_ms == ts_ms
    assert pkt.imu is None
    assert pkt.ultrasonic is None

def test_bin_telem_short_header_graceful():
    pkt = parse_telemetry_bin(b"\x01\x02")  # too short
    assert pkt.ts_ms == 0  # your implementation returns 0 on short header
