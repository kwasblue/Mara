# telemetry/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ImuTelemetry:
    online: bool
    ok: bool
    ax_g: Optional[float] = None
    ay_g: Optional[float] = None
    az_g: Optional[float] = None
    gx_dps: Optional[float] = None
    gy_dps: Optional[float] = None
    gz_dps: Optional[float] = None
    temp_c: Optional[float] = None


@dataclass
class UltrasonicTelemetry:
    sensor_id: int
    attached: bool
    ok: Optional[bool] = None
    distance_cm: Optional[float] = None
    ts_ms: Optional[int] = None


@dataclass
class LidarTelemetry:
    online: bool
    ok: bool
    distance_m: Optional[float] = None
    signal: Optional[float] = None
    ts_ms: Optional[int] = None


@dataclass
class EncoderTelemetry:
    ts_ms: int
    encoder_id: int
    ticks: int


@dataclass
class StepperTelemetry:
    ts_ms: int
    motor_id: Optional[int] = None
    attached: Optional[bool] = None
    enabled: Optional[bool] = None
    moving: Optional[bool] = None
    dir_forward: Optional[bool] = None
    last_cmd_steps: Optional[int] = None
    last_cmd_speed: Optional[float] = None


@dataclass
class DcMotorTelemetry:
    ts_ms: int
    motor_id: Optional[int] = None
    attached: Optional[bool] = None
    in1_pin: Optional[int] = None
    in2_pin: Optional[int] = None
    pwm_pin: Optional[int] = None
    ledc_channel: Optional[int] = None
    gpio_ch_in1: Optional[int] = None
    gpio_ch_in2: Optional[int] = None
    pwm_ch: Optional[int] = None
    speed: Optional[float] = None
    freq_hz: Optional[float] = None
    resolution_bits: Optional[int] = None


@dataclass
class PerformanceTelemetry:
    ts_ms: int
    last_fault: int
    hb_count: int
    hb_timeouts: int
    hb_recoveries: int
    hb_max_gap_ms: int
    motion_cmds: int
    motion_timeouts: int
    motion_max_gap_ms: int
    iterations: int
    overruns: int
    avg_total_us: int
    peak_total_us: int
    pkt_last_bytes: int
    pkt_max_bytes: int
    pkt_sent: int
    pkt_bytes: int
    pkt_dropped_sections: int
    pkt_last_sections: int
    pkt_max_sections: int
    pkt_buffered: int


@dataclass
class SensorHealthEntryTelemetry:
    kind: str
    sensor_id: int
    present: bool
    healthy: bool
    degraded: bool
    stale: bool
    detail: int = 0
    flags: int = 0


@dataclass
class SensorHealthTelemetry:
    ts_ms: int
    sensors: list[SensorHealthEntryTelemetry] = field(default_factory=list)


@dataclass
class SignalTelemetry:
    id: int
    name: str
    value: float
    ts_ms: int


@dataclass
class ControlSignalsTelemetry:
    signals: list
    count: int


@dataclass
class ObserverTelemetry:
    slot: int
    enabled: bool
    update_count: int
    states: list
    truncated: bool = False  # True if states were truncated due to malformed packet


@dataclass
class ControlObserversTelemetry:
    observers: list


@dataclass
class ControlSlotTelemetry:
    slot: int
    enabled: bool
    ok: bool
    run_count: int
    last_run_ms: Optional[int] = None


@dataclass
class ControlSlotsTelemetry:
    slots: list


@dataclass
class TelemetryPacket:
    ts_ms: int
    raw: Dict[str, Any]
    imu: Optional[ImuTelemetry] = None
    ultrasonic: Optional[UltrasonicTelemetry] = None
    lidar: Optional[LidarTelemetry] = None
    encoder0: Optional[EncoderTelemetry] = None
    stepper0: Optional[StepperTelemetry] = None
    dc_motor0: Optional[DcMotorTelemetry] = None
    perf: Optional[PerformanceTelemetry] = None
    sensor_health: Optional[SensorHealthTelemetry] = None
    ctrl_signals: Optional[ControlSignalsTelemetry] = None
    ctrl_observers: Optional[ControlObserversTelemetry] = None
    ctrl_slots: Optional[ControlSlotsTelemetry] = None


__all__ = [
    "ImuTelemetry",
    "UltrasonicTelemetry",
    "LidarTelemetry",
    "EncoderTelemetry",
    "StepperTelemetry",
    "DcMotorTelemetry",
    "PerformanceTelemetry",
    "SensorHealthEntryTelemetry",
    "SensorHealthTelemetry",
    "SignalTelemetry",
    "ControlSignalsTelemetry",
    "ObserverTelemetry",
    "ControlObserversTelemetry",
    "ControlSlotTelemetry",
    "ControlSlotsTelemetry",
    "TelemetryPacket",
]
