# telemetry/parser.py
from __future__ import annotations

from typing import Any, Dict, Optional

from .models import (
    TelemetryPacket,
    ImuTelemetry,
    UltrasonicTelemetry,
    LidarTelemetry,
    EncoderTelemetry,
    StepperTelemetry,
    DcMotorTelemetry,
    SensorHealthEntryTelemetry,
    SensorHealthTelemetry,
)


def _float_or_none(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int_or_none(v: Any) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def parse_telemetry(msg: Dict[str, Any]) -> TelemetryPacket:
    """
    Parse TELEMETRY JSON from MCU:

      {
        "src": "mcu",
        "type": "TELEMETRY",
        "ts_ms": <int>,
        "data": {
          "imu": {...},
          "ultrasonic": {...},
          "lidar": {...},
          "encoder0": {...},
          "stepper0": {...},
          "dc_motor0": {...}
        }
      }
    """
    ts_ms = int(msg.get("ts_ms", 0))
    data = msg.get("data") or {}

    # --- IMU ---
    imu = None
    imu_raw = data.get("imu")
    if isinstance(imu_raw, dict):
        imu = ImuTelemetry(
            online=bool(imu_raw.get("online", False)),
            ok=bool(imu_raw.get("ok", False)),
            ax_g=_float_or_none(imu_raw.get("ax_g")),
            ay_g=_float_or_none(imu_raw.get("ay_g")),
            az_g=_float_or_none(imu_raw.get("az_g")),
            gx_dps=_float_or_none(imu_raw.get("gx_dps")),
            gy_dps=_float_or_none(imu_raw.get("gy_dps")),
            gz_dps=_float_or_none(imu_raw.get("gz_dps")),
            temp_c=_float_or_none(imu_raw.get("temp_c")),
        )

    # --- Ultrasonic ---
    ultrasonic = None
    ultra_raw = data.get("ultrasonic")
    if isinstance(ultra_raw, dict):
        ultrasonic = UltrasonicTelemetry(
            sensor_id=int(ultra_raw.get("sensor_id", 0)),
            attached=bool(ultra_raw.get("attached", False)),
            ok=ultra_raw.get("ok"),
            distance_cm=_float_or_none(ultra_raw.get("distance_cm")),
            ts_ms=ts_ms,
        )

    # --- LiDAR ---
    lidar = None
    lidar_raw = data.get("lidar")
    if isinstance(lidar_raw, dict):
        lidar = LidarTelemetry(
            online=bool(lidar_raw.get("online", False)),
            ok=bool(lidar_raw.get("ok", False)),
            distance_m=_float_or_none(lidar_raw.get("distance_m")),
            # MCU doesn't send signal yet
            signal=_float_or_none(lidar_raw.get("signal")),
            ts_ms=ts_ms,
        )

    # --- Sensor health ---
    sensor_health = None
    sensor_health_raw = data.get("sensor_health")
    if isinstance(sensor_health_raw, dict):
        sensors = []
        for entry in sensor_health_raw.get("sensors", []):
            if not isinstance(entry, dict):
                continue
            sensors.append(
                SensorHealthEntryTelemetry(
                    kind=str(entry.get("kind", "unknown")),
                    sensor_id=int(entry.get("sensor_id", 0)),
                    present=bool(entry.get("present", False)),
                    healthy=bool(entry.get("healthy", False)),
                    degraded=bool(entry.get("degraded", False)),
                    stale=bool(entry.get("stale", False)),
                    detail=int(entry.get("detail", 0)),
                    flags=int(entry.get("flags", 0)),
                )
            )
        sensor_health = SensorHealthTelemetry(ts_ms=ts_ms, sensors=sensors)

    # --- Encoder0 ---
    encoder0 = None
    enc_raw = data.get("encoder0")
    if isinstance(enc_raw, dict):
        ticks = _int_or_none(enc_raw.get("ticks"))
        if ticks is not None:
            encoder0 = EncoderTelemetry(
                ts_ms=ts_ms,
                encoder_id=0,
                ticks=ticks,
            )

    # --- Stepper0 ---
    stepper0 = None
    step_raw = data.get("stepper0")
    if isinstance(step_raw, dict):
        stepper0 = StepperTelemetry(
            ts_ms=ts_ms,
            motor_id=_int_or_none(step_raw.get("motor_id")),
            attached=step_raw.get("attached"),
            enabled=step_raw.get("enabled"),
            moving=step_raw.get("moving"),
            dir_forward=step_raw.get("dir_forward"),
            last_cmd_steps=_int_or_none(step_raw.get("last_cmd_steps")),
            last_cmd_speed=_float_or_none(step_raw.get("last_cmd_speed")),
        )

    # --- DC motor 0 ---
    dc_motor0 = None
    dc_raw = data.get("dc_motor0")
    if isinstance(dc_raw, dict):
        dc_motor0 = DcMotorTelemetry(
            ts_ms=ts_ms,
            motor_id=_int_or_none(dc_raw.get("motor_id")),
            attached=dc_raw.get("attached"),

            in1_pin=_int_or_none(dc_raw.get("in1_pin")),
            in2_pin=_int_or_none(dc_raw.get("in2_pin")),
            pwm_pin=_int_or_none(dc_raw.get("pwm_pin")),
            ledc_channel=_int_or_none(dc_raw.get("ledc_channel")),

            gpio_ch_in1=_int_or_none(dc_raw.get("gpio_ch_in1")),
            gpio_ch_in2=_int_or_none(dc_raw.get("gpio_ch_in2")),
            pwm_ch=_int_or_none(dc_raw.get("pwm_ch")),

            speed=_float_or_none(dc_raw.get("speed")),
            freq_hz=_float_or_none(dc_raw.get("freq_hz")),
            resolution_bits=_int_or_none(dc_raw.get("resolution_bits")),
        )

    return TelemetryPacket(
        ts_ms=ts_ms,
        raw=msg,
        imu=imu,
        ultrasonic=ultrasonic,
        lidar=lidar,
        encoder0=encoder0,
        stepper0=stepper0,
        dc_motor0=dc_motor0,
        sensor_health=sensor_health,
    )
