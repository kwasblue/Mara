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
    SignalTelemetry,
    ControlSignalsTelemetry,
    ObserverTelemetry,
    ControlObserversTelemetry,
    ControlSlotTelemetry,
    ControlSlotsTelemetry,
)

# Section IDs (auto-generated from platform_schema.py)
from .telemetry_sections import (
    TELEM_IMU,
    TELEM_ULTRASONIC,
    TELEM_LIDAR,
    TELEM_ENCODER0,
    TELEM_STEPPER0,
    TELEM_DC_MOTOR0,
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
_SIGNAL_FMT = struct.Struct("<Hfi")  # id, value, ts_ms
_OBSERVER_HDR_FMT = struct.Struct("<BBB")  # slot, enabled, num_states
_FLOAT_FMT = struct.Struct("<f")  # single float
_SLOT_FMT = struct.Struct("<BBBI")  # slot, enabled, ok, run_count
_U16_FMT = struct.Struct("<H")  # count

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
        ctrl_signals=None,
        ctrl_observers=None,
        ctrl_slots=None,
    )

def parse_telemetry_bin(payload: bytes) -> TelemetryPacket:
    """
    Parse a *sectioned* binary telemetry payload (the bytes after MSG_TELEMETRY_BIN).
    Format (LE):
      u8  version (=1)
      u16 seq
      u32 ts_ms
      u8  section_count
      repeat:
        u8  section_id
        u16 section_len
        u8[] section_bytes
    """
    if len(payload) < _PKT_HDR.size:
        return _make_empty(0, len(payload), {"error": "short_header"})

    ver, seq, ts_ms, section_count = _PKT_HDR.unpack_from(payload, 0)
    off = _PKT_HDR.size

    pkt = _make_empty(ts_ms, len(payload), {"ver": int(ver), "seq": int(seq), "sections": int(section_count)})

    # Parse each section
    for _ in range(int(section_count)):
        if off + 3 > len(payload):
            pkt.raw["error"] = "short_section_header"
            return pkt

        section_id = payload[off]
        section_len = int.from_bytes(payload[off + 1 : off + 3], "little")
        off += 3

        if off + section_len > len(payload):
            pkt.raw["error"] = "short_section_body"
            pkt.raw["bad_section_id"] = int(section_id)
            pkt.raw["needed"] = section_len
            pkt.raw["have"] = len(payload) - off
            return pkt

        body = payload[off : off + section_len]
        off += section_len

        # ---- Section decoders (v1) ----
        # Using pre-compiled Struct objects and multiplication for speed

        # IMU v1:
        # online(u8), ok(u8),
        # ax_mg(i16), ay_mg(i16), az_mg(i16),
        # gx_mdps(i16), gy_mdps(i16), gz_mdps(i16),
        # temp_c_centi(i16)
        if section_id == TELEM_IMU:
            if len(body) >= _IMU_FMT.size:
                online, ok, ax_mg, ay_mg, az_mg, gx_mdps, gy_mdps, gz_mdps, temp_c_centi = _IMU_FMT.unpack_from(body, 0)
                pkt.imu = ImuTelemetry(
                    online=bool(online),
                    ok=bool(ok),
                    ax_g=ax_mg * 0.001,
                    ay_g=ay_mg * 0.001,
                    az_g=az_mg * 0.001,
                    gx_dps=gx_mdps * 0.001,
                    gy_dps=gy_mdps * 0.001,
                    gz_dps=gz_mdps * 0.001,
                    temp_c=temp_c_centi * 0.01,
                )
            continue

        # Ultrasonic v1:
        # sensor_id(u8), attached(u8), ok(u8), dist_mm(u16)
        if section_id == TELEM_ULTRASONIC:
            if len(body) >= _ULTRASONIC_FMT.size:
                sensor_id, attached, ok, dist_mm = _ULTRASONIC_FMT.unpack_from(body, 0)
                pkt.ultrasonic = UltrasonicTelemetry(
                    sensor_id=int(sensor_id),
                    attached=bool(attached),
                    ok=bool(ok),
                    distance_cm=(dist_mm * 0.1) if dist_mm != 0 else None,
                    ts_ms=ts_ms,
                )
            continue

        # LiDAR v1:
        # online(u8), ok(u8), dist_mm(u16), signal(u16)
        if section_id == TELEM_LIDAR:
            if len(body) >= _LIDAR_FMT.size:
                online, ok, dist_mm, signal = _LIDAR_FMT.unpack_from(body, 0)
                pkt.lidar = LidarTelemetry(
                    online=bool(online),
                    ok=bool(ok),
                    distance_m=(dist_mm * 0.001) if dist_mm != 0 else None,
                    signal=(signal if signal != 0 else None),
                    ts_ms=ts_ms,
                )
            continue

        # Encoder0 v1:
        # ticks(i32)
        if section_id == TELEM_ENCODER0:
            if len(body) >= _ENCODER_FMT.size:
                (ticks,) = _ENCODER_FMT.unpack_from(body, 0)
                pkt.encoder0 = EncoderTelemetry(ts_ms=ts_ms, encoder_id=0, ticks=ticks)
            continue

        # Stepper0 v1:
        # motor_id(i8), attached(u8), enabled(u8), moving(u8), dir_forward(u8),
        # last_cmd_steps(i32), last_cmd_speed_centi(i16)
        if section_id == TELEM_STEPPER0:
            if len(body) >= _STEPPER_FMT.size:
                motor_id, attached, enabled, moving, dir_forward, last_steps, speed_centi = _STEPPER_FMT.unpack_from(body, 0)
                pkt.stepper0 = StepperTelemetry(
                    ts_ms=ts_ms,
                    motor_id=motor_id,
                    attached=bool(attached),
                    enabled=bool(enabled),
                    moving=bool(moving),
                    dir_forward=bool(dir_forward),
                    last_cmd_steps=last_steps,
                    last_cmd_speed=speed_centi * 0.01,
                )
            continue

        # DC Motor0 v1 (minimal):
        # attached(u8), speed_centi(i16)
        if section_id == TELEM_DC_MOTOR0:
            if len(body) >= _DC_MOTOR_FMT.size:
                attached, speed_centi = _DC_MOTOR_FMT.unpack_from(body, 0)
                pkt.dc_motor0 = DcMotorTelemetry(
                    ts_ms=ts_ms,
                    motor_id=0,
                    attached=bool(attached),
                    in1_pin=None, in2_pin=None, pwm_pin=None, ledc_channel=None,
                    gpio_ch_in1=None, gpio_ch_in2=None, pwm_ch=None,
                    speed=speed_centi * 0.01,
                    freq_hz=None,
                    resolution_bits=None,
                )
            continue

        # Control Signals:
        # count(u16), [id(u16), value(f32), ts_ms(u32)] * count
        if section_id == TELEM_CTRL_SIGNALS:
            if len(body) >= _U16_FMT.size:
                count = _U16_FMT.unpack_from(body, 0)[0]
                signals = []
                pos = 2
                signal_size = _SIGNAL_FMT.size
                for _ in range(count):
                    if pos + signal_size > len(body):
                        break
                    sig_id, value, sig_ts = _SIGNAL_FMT.unpack_from(body, pos)
                    signals.append(SignalTelemetry(id=sig_id, name="", value=value, ts_ms=sig_ts))
                    pos += signal_size
                pkt.ctrl_signals = ControlSignalsTelemetry(signals=signals, count=count)
            continue

        # Control Observers:
        # slot_count(u8), [slot(u8), enabled(u8), num_states(u8), x[0]:f32...] * slot_count
        if section_id == TELEM_CTRL_OBSERVERS:
            if len(body) >= 1:
                slot_count = body[0]
                observers = []
                pos = 1
                obs_hdr_size = _OBSERVER_HDR_FMT.size
                float_size = _FLOAT_FMT.size
                for _ in range(slot_count):
                    if pos + obs_hdr_size > len(body):
                        break
                    slot, enabled, num_states = _OBSERVER_HDR_FMT.unpack_from(body, pos)
                    pos += obs_hdr_size
                    states = []
                    for _ in range(num_states):
                        if pos + float_size > len(body):
                            break
                        (x,) = _FLOAT_FMT.unpack_from(body, pos)
                        states.append(x)
                        pos += float_size
                    observers.append(ObserverTelemetry(
                        slot=slot, enabled=bool(enabled), update_count=0, states=states
                    ))
                pkt.ctrl_observers = ControlObserversTelemetry(observers=observers)
            continue

        # Control Slots:
        # slot_count(u8), [slot(u8), enabled(u8), ok(u8), run_count(u32)] * slot_count
        if section_id == TELEM_CTRL_SLOTS:
            if len(body) >= 1:
                slot_count = body[0]
                slots = []
                pos = 1
                slot_size = _SLOT_FMT.size
                for _ in range(slot_count):
                    if pos + slot_size > len(body):
                        break
                    slot, enabled, ok, run_count = _SLOT_FMT.unpack_from(body, pos)
                    pos += slot_size
                    slots.append(ControlSlotTelemetry(
                        slot=slot, enabled=bool(enabled), ok=bool(ok), run_count=run_count
                    ))
                pkt.ctrl_slots = ControlSlotsTelemetry(slots=slots)
            continue

        # Unknown section_id -> ignore (forward-compatible)
        # You can store stats if you want:
        # pkt.raw.setdefault("unknown_sections", []).append(int(section_id))

    return pkt
