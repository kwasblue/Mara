# telemetry/binary_parser.py
from __future__ import annotations

import struct
from typing import Dict, Any

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
        return _make_empty(0, len(payload), {"error": "short_header"})

    ver, seq, ts_ms, section_count = _PKT_HDR.unpack_from(payload, 0)
    off = _PKT_HDR.size
    pkt = _make_empty(ts_ms, len(payload), {"ver": int(ver), "seq": int(seq), "sections": int(section_count)})

    for _ in range(int(section_count)):
        if off + 3 > len(payload):
            pkt.raw["error"] = "short_section_header"
            return pkt

        section_id = payload[off]
        section_len = int.from_bytes(payload[off + 1: off + 3], "little")
        off += 3

        if off + section_len > len(payload):
            pkt.raw["error"] = "short_section_body"
            pkt.raw["bad_section_id"] = int(section_id)
            pkt.raw["needed"] = section_len
            pkt.raw["have"] = len(payload) - off
            return pkt

        body = payload[off: off + section_len]
        off += section_len

        if section_id == TELEM_IMU:
            if len(body) >= _IMU_FMT.size:
                online, ok, ax_mg, ay_mg, az_mg, gx_mdps, gy_mdps, gz_mdps, temp_c_centi = _IMU_FMT.unpack_from(body, 0)
                pkt.imu = ImuTelemetry(bool(online), bool(ok), ax_mg * 0.001, ay_mg * 0.001, az_mg * 0.001, gx_mdps * 0.001, gy_mdps * 0.001, gz_mdps * 0.001, temp_c_centi * 0.01)
            continue

        if section_id == TELEM_ULTRASONIC:
            if len(body) >= _ULTRASONIC_FMT.size:
                sensor_id, attached, ok, dist_mm = _ULTRASONIC_FMT.unpack_from(body, 0)
                pkt.ultrasonic = UltrasonicTelemetry(int(sensor_id), bool(attached), bool(ok), (dist_mm * 0.1) if dist_mm != 0 else None, ts_ms)
            continue

        if section_id == TELEM_LIDAR:
            if len(body) >= _LIDAR_FMT.size:
                online, ok, dist_mm, signal = _LIDAR_FMT.unpack_from(body, 0)
                pkt.lidar = LidarTelemetry(bool(online), bool(ok), (dist_mm * 0.001) if dist_mm != 0 else None, (signal if signal != 0 else None), ts_ms)
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
                for _ in range(count):
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
                for _ in range(count):
                    if pos + _SIGNAL_FMT.size > len(body):
                        break
                    sig_id, value, sig_ts = _SIGNAL_FMT.unpack_from(body, pos)
                    signals.append(SignalTelemetry(id=sig_id, name="", value=value, ts_ms=sig_ts))
                    pos += _SIGNAL_FMT.size
                pkt.ctrl_signals = ControlSignalsTelemetry(signals=signals, count=count)
            continue

        if section_id == TELEM_CTRL_OBSERVERS:
            if len(body) >= 1:
                slot_count = body[0]
                observers = []
                pos = 1
                for _ in range(slot_count):
                    if pos + _OBSERVER_HDR_FMT.size > len(body):
                        break
                    slot, enabled, num_states = _OBSERVER_HDR_FMT.unpack_from(body, pos)
                    pos += _OBSERVER_HDR_FMT.size
                    states = []
                    for _ in range(num_states):
                        if pos + _FLOAT_FMT.size > len(body):
                            break
                        (x,) = _FLOAT_FMT.unpack_from(body, pos)
                        states.append(x)
                        pos += _FLOAT_FMT.size
                    observers.append(ObserverTelemetry(slot=slot, enabled=bool(enabled), update_count=0, states=states))
                pkt.ctrl_observers = ControlObserversTelemetry(observers=observers)
            continue

        if section_id == TELEM_CTRL_SLOTS:
            if len(body) >= 1:
                slot_count = body[0]
                slots = []
                pos = 1
                for _ in range(slot_count):
                    if pos + _SLOT_FMT.size > len(body):
                        break
                    slot, enabled, ok, run_count = _SLOT_FMT.unpack_from(body, pos)
                    pos += _SLOT_FMT.size
                    slots.append(ControlSlotTelemetry(slot=slot, enabled=bool(enabled), ok=bool(ok), run_count=run_count))
                pkt.ctrl_slots = ControlSlotsTelemetry(slots=slots)
            continue

    return pkt
