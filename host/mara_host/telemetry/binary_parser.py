# telemetry/binary_parser.py
from __future__ import annotations

import logging
import struct
from typing import Dict, Any

_log = logging.getLogger(__name__)

from .models import (
    TelemetryPacket,
    ImuTelemetry,
    UltrasonicTelemetry,
    LidarTelemetry,
    EncoderTelemetry,
    StepperTelemetry,
    DcMotorTelemetry,
    PerformanceTelemetry,
    SensorHealthEntryTelemetry,
    SensorHealthTelemetry,
    SignalTelemetry,
    ControlSignalsTelemetry,
    ObserverTelemetry,
    ControlObserversTelemetry,
    ControlSlotTelemetry,
    ControlSlotsTelemetry,
)

# Section IDs (auto-generated from schema/telemetry.py)
from .telemetry_sections import (
    TELEM_IMU,
    TELEM_ULTRASONIC,
    TELEM_LIDAR,
    TELEM_ENCODER0,
    TELEM_STEPPER0,
    TELEM_DC_MOTOR0,
    TELEM_PERF,
    TELEM_SENSOR_HEALTH,
    TELEM_CTRL_SIGNALS,
    TELEM_CTRL_OBSERVERS,
    TELEM_CTRL_SLOTS,
)

# Pre-compiled struct formats for performance (avoid format string parsing each call)
_PKT_HDR = struct.Struct("<BHIB")  # version(u8), seq(u16), ts_ms(u32), section_count(u8)
_SECTION_HDR = struct.Struct("<BH")  # section_id(u8), section_len(u16) - optimized from int.from_bytes

# Maximum section size to prevent DoS via malformed packets
_MAX_SECTION_SIZE = 4096
_IMU_FMT = struct.Struct("<BB7h")  # online, ok, ax/ay/az, gx/gy/gz, temp
_ULTRASONIC_FMT = struct.Struct("<BBBH")  # sensor_id, attached, ok, dist_mm
_LIDAR_FMT = struct.Struct("<BBHH")  # online, ok, dist_mm, signal
_ENCODER_FMT = struct.Struct("<i")  # ticks
_STEPPER_FMT = struct.Struct("<bBBBBih")  # motor_id, attached, enabled, moving, dir, steps, speed
_DC_MOTOR_FMT = struct.Struct("<Bh")  # attached, speed_centi
_PERF_FMT = struct.Struct("<BIIIIIIIIIHHHHIII3B")
_SIGNAL_FMT = struct.Struct("<Hfi")  # id, value, ts_ms
_OBSERVER_HDR_FMT = struct.Struct("<BBB")  # slot, enabled, num_states
_FLOAT_FMT = struct.Struct("<f")  # single float
_SLOT_FMT = struct.Struct("<BBBI")  # slot, enabled, ok, run_count
_U16_FMT = struct.Struct("<H")  # count
_SENSOR_HEALTH_ENTRY_FMT = struct.Struct("<BBBB")  # kind, sensor_id, flags, detail

# Sentinel value for "no measurement" (0xFFFF = 65535)
# Zero distance is valid (object touching sensor), so we use max uint16 as sentinel
_NO_MEASUREMENT_SENTINEL = 0xFFFF

_SENSOR_KIND_NAMES = {
    1: "imu",
    2: "ultrasonic",
    3: "lidar",
    4: "encoder",
}


def _make_empty(ts_ms: int, raw_len: int, meta: Dict[str, Any]) -> TelemetryPacket:
    return TelemetryPacket(
        ts_ms=ts_ms,
        raw=meta | {"bin": True, "len": raw_len},
        imu=None,
        ultrasonic=None,
        lidar=None,
        encoder0=None,
        stepper0=None,
        dc_motor0=None,
        perf=None,
        sensor_health=None,
        ctrl_signals=None,
        ctrl_observers=None,
        ctrl_slots=None,
    )


def parse_telemetry_bin(payload: bytes) -> TelemetryPacket:
    if len(payload) < _PKT_HDR.size:
        _log.warning("Telemetry packet too short: %d bytes (need %d for header)", len(payload), _PKT_HDR.size)
        return _make_empty(0, len(payload), {"error": "short_header"})

    ver, seq, ts_ms, section_count = _PKT_HDR.unpack_from(payload, 0)
    off = _PKT_HDR.size
    pkt = _make_empty(ts_ms, len(payload), {"ver": int(ver), "seq": int(seq), "sections": int(section_count)})

    # Use memoryview to avoid slice copies in hot loop
    payload_view = memoryview(payload)

    for _ in range(int(section_count)):
        if off + _SECTION_HDR.size > len(payload):
            _log.warning("Telemetry section header truncated at offset %d (payload len=%d)", off, len(payload))
            pkt.raw["error"] = "short_section_header"
            return pkt

        # Optimized: use pre-compiled struct instead of int.from_bytes with slice
        section_id, section_len = _SECTION_HDR.unpack_from(payload, off)
        off += _SECTION_HDR.size

        # Sanity check: reject unreasonably large sections (DoS prevention)
        if section_len > _MAX_SECTION_SIZE:
            _log.warning("Telemetry section 0x%02X too large: %d bytes (max %d)", section_id, section_len, _MAX_SECTION_SIZE)
            pkt.raw["error"] = f"section_too_large:{section_len}"
            pkt.raw["bad_section_id"] = int(section_id)
            return pkt

        if off + section_len > len(payload):
            _log.warning(
                "Telemetry section 0x%02X body truncated: need %d bytes, have %d",
                section_id, section_len, len(payload) - off
            )
            pkt.raw["error"] = "short_section_body"
            pkt.raw["bad_section_id"] = int(section_id)
            pkt.raw["needed"] = section_len
            pkt.raw["have"] = len(payload) - off
            return pkt

        # Use memoryview slice (O(1) no-copy) instead of bytes slice (O(n) copy)
        body = payload_view[off: off + section_len]
        off += section_len

        if section_id == TELEM_IMU:
            if len(body) >= _IMU_FMT.size:
                online, ok, ax_mg, ay_mg, az_mg, gx_mdps, gy_mdps, gz_mdps, temp_c_centi = _IMU_FMT.unpack_from(body, 0)
                pkt.imu = ImuTelemetry(bool(online), bool(ok), ax_mg * 0.001, ay_mg * 0.001, az_mg * 0.001, gx_mdps * 0.001, gy_mdps * 0.001, gz_mdps * 0.001, temp_c_centi * 0.01)
            continue

        if section_id == TELEM_ULTRASONIC:
            if len(body) >= _ULTRASONIC_FMT.size:
                sensor_id, attached, ok, dist_mm = _ULTRASONIC_FMT.unpack_from(body, 0)
                # Use sentinel value for "no measurement" - zero distance is valid (object touching sensor)
                distance_cm = (dist_mm * 0.1) if dist_mm != _NO_MEASUREMENT_SENTINEL else None
                pkt.ultrasonic = UltrasonicTelemetry(int(sensor_id), bool(attached), bool(ok), distance_cm, ts_ms)
            continue

        if section_id == TELEM_LIDAR:
            if len(body) >= _LIDAR_FMT.size:
                online, ok, dist_mm, signal = _LIDAR_FMT.unpack_from(body, 0)
                # Use sentinel value for "no measurement" - zero distance is valid
                distance_m = (dist_mm * 0.001) if dist_mm != _NO_MEASUREMENT_SENTINEL else None
                signal_val = signal if signal != _NO_MEASUREMENT_SENTINEL else None
                pkt.lidar = LidarTelemetry(bool(online), bool(ok), distance_m, signal_val, ts_ms)
            continue

        if section_id == TELEM_ENCODER0:
            if len(body) >= _ENCODER_FMT.size:
                (ticks,) = _ENCODER_FMT.unpack_from(body, 0)
                pkt.encoder0 = EncoderTelemetry(ts_ms=ts_ms, encoder_id=0, ticks=ticks)
            continue

        if section_id == TELEM_STEPPER0:
            if len(body) >= _STEPPER_FMT.size:
                motor_id, attached, enabled, moving, dir_forward, last_steps, speed_centi = _STEPPER_FMT.unpack_from(body, 0)
                pkt.stepper0 = StepperTelemetry(ts_ms=ts_ms, motor_id=motor_id, attached=bool(attached), enabled=bool(enabled), moving=bool(moving), dir_forward=bool(dir_forward), last_cmd_steps=last_steps, last_cmd_speed=speed_centi * 0.01)
            continue

        if section_id == TELEM_DC_MOTOR0:
            if len(body) >= _DC_MOTOR_FMT.size:
                attached, speed_centi = _DC_MOTOR_FMT.unpack_from(body, 0)
                pkt.dc_motor0 = DcMotorTelemetry(ts_ms=ts_ms, motor_id=0, attached=bool(attached), speed=speed_centi * 0.01)
            continue

        if section_id == TELEM_PERF:
            if len(body) >= _PERF_FMT.size:
                values = _PERF_FMT.unpack_from(body, 0)
                pkt.perf = PerformanceTelemetry(ts_ms=ts_ms, last_fault=values[0], hb_count=values[1], hb_timeouts=values[2], hb_recoveries=values[3], hb_max_gap_ms=values[4], motion_cmds=values[5], motion_timeouts=values[6], motion_max_gap_ms=values[7], iterations=values[8], overruns=values[9], avg_total_us=values[10], peak_total_us=values[11], pkt_last_bytes=values[12], pkt_max_bytes=values[13], pkt_sent=values[14], pkt_bytes=values[15], pkt_dropped_sections=values[16], pkt_last_sections=values[17], pkt_max_sections=values[18], pkt_buffered=values[19])
            continue

        if section_id == TELEM_SENSOR_HEALTH:
            if len(body) >= 1:
                count = body[0]
                sensors = []
                pos = 1
                # Limit iterations to available data (prevents wasted loop iterations)
                max_entries = (len(body) - pos) // _SENSOR_HEALTH_ENTRY_FMT.size
                for _ in range(min(count, max_entries)):
                    if pos + _SENSOR_HEALTH_ENTRY_FMT.size > len(body):
                        break
                    kind_code, sensor_id, flags, detail = _SENSOR_HEALTH_ENTRY_FMT.unpack_from(body, pos)
                    pos += _SENSOR_HEALTH_ENTRY_FMT.size
                    sensors.append(
                        SensorHealthEntryTelemetry(
                            kind=_SENSOR_KIND_NAMES.get(kind_code, f"kind_{kind_code}"),
                            sensor_id=int(sensor_id),
                            present=bool(flags & 0x01),
                            healthy=bool(flags & 0x02),
                            degraded=bool(flags & 0x04),
                            stale=bool(flags & 0x08),
                            detail=int(detail),
                            flags=int(flags),
                        )
                    )
                pkt.sensor_health = SensorHealthTelemetry(ts_ms=ts_ms, sensors=sensors)
            continue

        if section_id == TELEM_CTRL_SIGNALS:
            if len(body) >= _U16_FMT.size:
                count = _U16_FMT.unpack_from(body, 0)[0]
                signals = []
                pos = 2
                # Bound loop iterations by available data (prevents 65535-iteration range)
                max_entries = (len(body) - pos) // _SIGNAL_FMT.size
                for _ in range(min(count, max_entries)):
                    if pos + _SIGNAL_FMT.size > len(body):
                        break
                    sig_id, value, sig_ts = _SIGNAL_FMT.unpack_from(body, pos)
                    signals.append(SignalTelemetry(id=sig_id, name="", value=value, ts_ms=sig_ts))
                    pos += _SIGNAL_FMT.size
                # Use len(signals) as actual count, not wire value (corrupt packet could claim count=60000)
                pkt.ctrl_signals = ControlSignalsTelemetry(signals=signals, count=len(signals))
            continue

        if section_id == TELEM_CTRL_OBSERVERS:
            if len(body) >= 1:
                slot_count = body[0]
                observers = []
                pos = 1
                # Bound by minimum entry size (header only, states are variable)
                max_entries = (len(body) - pos) // _OBSERVER_HDR_FMT.size
                for _ in range(min(slot_count, max_entries)):
                    if pos + _OBSERVER_HDR_FMT.size > len(body):
                        break
                    slot, enabled, num_states = _OBSERVER_HDR_FMT.unpack_from(body, pos)
                    pos += _OBSERVER_HDR_FMT.size
                    states = []
                    # Bound inner loop by available data
                    max_states = (len(body) - pos) // _FLOAT_FMT.size
                    for _ in range(min(num_states, max_states)):
                        if pos + _FLOAT_FMT.size > len(body):
                            break
                        (x,) = _FLOAT_FMT.unpack_from(body, pos)
                        states.append(x)
                        pos += _FLOAT_FMT.size
                    # Track if states were truncated due to insufficient data
                    truncated = len(states) < num_states
                    if truncated:
                        _log.warning("Observer slot %d states truncated: expected %d, got %d", slot, num_states, len(states))
                    observers.append(ObserverTelemetry(slot=slot, enabled=bool(enabled), update_count=0, states=states, truncated=truncated))
                pkt.ctrl_observers = ControlObserversTelemetry(observers=observers)
            continue

        if section_id == TELEM_CTRL_SLOTS:
            if len(body) >= 1:
                slot_count = body[0]
                slots = []
                pos = 1
                # Bound loop iterations by available data
                max_entries = (len(body) - pos) // _SLOT_FMT.size
                for _ in range(min(slot_count, max_entries)):
                    if pos + _SLOT_FMT.size > len(body):
                        break
                    slot, enabled, ok, run_count = _SLOT_FMT.unpack_from(body, pos)
                    pos += _SLOT_FMT.size
                    slots.append(ControlSlotTelemetry(slot=slot, enabled=bool(enabled), ok=bool(ok), run_count=run_count))
                pkt.ctrl_slots = ControlSlotsTelemetry(slots=slots)
            continue

        # Fallback: try auto-discovered sections from registry
        # This enables 1-file extensibility for new telemetry sections
        try:
            from .section_registry import parse_unknown_section
            parsed = parse_unknown_section(section_id, body, ts_ms)
            if parsed is not None:
                # Store in raw dict under section ID key
                pkt.raw[f"section_0x{section_id:02X}"] = parsed
        except ImportError:
            pass

    return pkt
