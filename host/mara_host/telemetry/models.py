# telemetry/models.py
from __future__ import annotations

from dataclasses import dataclass
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
    signal: Optional[float] = None  # MCU doesn't send this yet; fine as optional
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

    speed: Optional[float] = None          # -1.0..+1.0
    freq_hz: Optional[float] = None
    resolution_bits: Optional[int] = None


# -----------------------------------------------------------------------------
# Control System Telemetry
# -----------------------------------------------------------------------------

@dataclass
class SignalTelemetry:
    """Single signal from the signal bus."""
    id: int
    name: str
    value: float
    ts_ms: int


@dataclass
class ControlSignalsTelemetry:
    """All signals from the signal bus."""
    signals: list  # List[SignalTelemetry]
    count: int


@dataclass
class ObserverTelemetry:
    """Single observer state estimate."""
    slot: int
    enabled: bool
    update_count: int
    states: list  # List[float] - x_hat estimates


@dataclass
class ControlObserversTelemetry:
    """All observer states."""
    observers: list  # List[ObserverTelemetry]


@dataclass
class ControlSlotTelemetry:
    """Single control slot status."""
    slot: int
    enabled: bool
    ok: bool
    run_count: int
    last_run_ms: Optional[int] = None


@dataclass
class ControlSlotsTelemetry:
    """All control slot statuses."""
    slots: list  # List[ControlSlotTelemetry]


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

    # Control system telemetry
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
    "SignalTelemetry",
    "ControlSignalsTelemetry",
    "ObserverTelemetry",
    "ControlObserversTelemetry",
    "ControlSlotTelemetry",
    "ControlSlotsTelemetry",
    "TelemetryPacket",
]
