"""
Typed service response data classes.

These dataclasses provide type safety for the data returned by service operations.
They are used within ServiceResult.data to give typed access to response fields.

Usage:
    result = await gpio_service.read(0)
    if result.ok:
        reading = GpioReadResponse.from_dict(result.data)
        print(f"Channel {reading.channel}: {reading.value}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# =============================================================================
# GPIO Responses
# =============================================================================

@dataclass(frozen=True, slots=True)
class GpioReadResponse:
    """Response from a GPIO read operation."""

    channel: int
    value: int
    pin: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GpioReadResponse:
        """Parse from dict."""
        return cls(
            channel=data.get("channel", 0),
            value=data.get("value", 0),
            pin=data.get("pin"),
        )


@dataclass(frozen=True, slots=True)
class GpioWriteResponse:
    """Response from a GPIO write operation."""

    channel: int
    value: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GpioWriteResponse:
        """Parse from dict."""
        return cls(
            channel=data.get("channel", 0),
            value=data.get("value", 0),
        )


@dataclass(frozen=True, slots=True)
class GpioRegisterResponse:
    """Response from a GPIO register operation."""

    channel: int
    pin: int
    mode: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GpioRegisterResponse:
        """Parse from dict."""
        return cls(
            channel=data.get("channel", 0),
            pin=data.get("pin", 0),
            mode=data.get("mode", "output"),
        )


# =============================================================================
# Encoder Responses
# =============================================================================

@dataclass(frozen=True, slots=True)
class EncoderReadResponse:
    """Response from an encoder read operation."""

    encoder_id: int
    ticks: int
    velocity: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EncoderReadResponse:
        """Parse from dict."""
        return cls(
            encoder_id=data.get("encoder_id", 0),
            ticks=data.get("ticks", 0),
            velocity=data.get("velocity", 0.0),
        )


@dataclass(frozen=True, slots=True)
class EncoderAttachResponse:
    """Response from an encoder attach operation."""

    encoder_id: int
    pin_a: int
    pin_b: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EncoderAttachResponse:
        """Parse from dict."""
        return cls(
            encoder_id=data.get("encoder_id", 0),
            pin_a=data.get("pin_a", 0),
            pin_b=data.get("pin_b", 0),
        )


@dataclass(frozen=True, slots=True)
class EncoderResetResponse:
    """Response from an encoder reset operation."""

    encoder_id: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EncoderResetResponse:
        """Parse from dict."""
        return cls(encoder_id=data.get("encoder_id", 0))


@dataclass(frozen=True, slots=True)
class EncoderDetachResponse:
    """Response from an encoder detach operation."""

    encoder_id: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EncoderDetachResponse:
        """Parse from dict."""
        return cls(encoder_id=data.get("encoder_id", 0))


# =============================================================================
# Servo Responses
# =============================================================================

@dataclass(frozen=True, slots=True)
class ServoAttachResponse:
    """Response from a servo attach operation."""

    servo_id: int
    channel: int
    min_us: int = 1000
    max_us: int = 2000

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServoAttachResponse:
        """Parse from dict."""
        return cls(
            servo_id=data.get("servo_id", 0),
            channel=data.get("channel", 0),
            min_us=data.get("min_us", 1000),
            max_us=data.get("max_us", 2000),
        )


@dataclass(frozen=True, slots=True)
class ServoSetAngleResponse:
    """Response from a servo set angle operation."""

    servo_id: int
    angle_deg: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServoSetAngleResponse:
        """Parse from dict."""
        return cls(
            servo_id=data.get("servo_id", 0),
            angle_deg=data.get("angle_deg", 0.0),
        )


@dataclass(frozen=True, slots=True)
class ServoDetachResponse:
    """Response from a servo detach operation."""

    servo_id: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServoDetachResponse:
        """Parse from dict."""
        return cls(servo_id=data.get("servo_id", 0))


@dataclass(frozen=True, slots=True)
class ServoSetPulseResponse:
    """Response from a servo set pulse operation."""

    servo_id: int
    pulse_us: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServoSetPulseResponse:
        """Parse from dict."""
        return cls(
            servo_id=data.get("servo_id", 0),
            pulse_us=data.get("pulse_us", 1500),
        )


# =============================================================================
# Motor Responses
# =============================================================================

@dataclass(frozen=True, slots=True)
class MotorSetSpeedResponse:
    """Response from a motor set speed operation."""

    motor_id: int
    speed: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MotorSetSpeedResponse:
        """Parse from dict."""
        return cls(
            motor_id=data.get("motor_id", 0),
            speed=data.get("speed", 0.0),
        )


@dataclass(frozen=True, slots=True)
class MotorAttachResponse:
    """Response from a motor attach operation."""

    motor_id: int
    pin_pwm: int
    pin_dir: Optional[int] = None
    pin_dir_b: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MotorAttachResponse:
        """Parse from dict."""
        return cls(
            motor_id=data.get("motor_id", 0),
            pin_pwm=data.get("pin_pwm", 0),
            pin_dir=data.get("pin_dir"),
            pin_dir_b=data.get("pin_dir_b"),
        )


@dataclass(frozen=True, slots=True)
class MotorStopResponse:
    """Response from a motor stop operation."""

    motor_id: int
    brake: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MotorStopResponse:
        """Parse from dict."""
        return cls(
            motor_id=data.get("motor_id", 0),
            brake=data.get("brake", False),
        )


@dataclass(frozen=True, slots=True)
class MotorDetachResponse:
    """Response from a motor detach operation."""

    motor_id: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MotorDetachResponse:
        """Parse from dict."""
        return cls(motor_id=data.get("motor_id", 0))


# =============================================================================
# Stepper Responses
# =============================================================================

@dataclass(frozen=True, slots=True)
class StepperEnableResponse:
    """Response from a stepper enable/disable operation."""

    stepper_id: int
    enabled: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepperEnableResponse:
        """Parse from dict."""
        return cls(
            stepper_id=data.get("stepper_id", 0),
            enabled=data.get("enabled", False),
        )


@dataclass(frozen=True, slots=True)
class StepperMoveRelResponse:
    """Response from a stepper move relative operation."""

    stepper_id: int
    steps: int
    speed_rps: float = 1.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepperMoveRelResponse:
        """Parse from dict."""
        return cls(
            stepper_id=data.get("stepper_id", 0),
            steps=data.get("steps", 0),
            speed_rps=data.get("speed_rps", 1.0),
        )


@dataclass(frozen=True, slots=True)
class StepperMoveDegResponse:
    """Response from a stepper move degrees operation."""

    stepper_id: int
    degrees: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepperMoveDegResponse:
        """Parse from dict."""
        return cls(
            stepper_id=data.get("stepper_id", 0),
            degrees=data.get("degrees", 0.0),
        )


@dataclass(frozen=True, slots=True)
class StepperMoveRevResponse:
    """Response from a stepper move revolutions operation."""

    stepper_id: int
    revolutions: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepperMoveRevResponse:
        """Parse from dict."""
        return cls(
            stepper_id=data.get("stepper_id", 0),
            revolutions=data.get("revolutions", 0.0),
        )


@dataclass(frozen=True, slots=True)
class StepperStopResponse:
    """Response from a stepper stop operation."""

    stepper_id: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepperStopResponse:
        """Parse from dict."""
        return cls(stepper_id=data.get("stepper_id", 0))


@dataclass(frozen=True, slots=True)
class StepperPositionResponse:
    """Response from a stepper get/reset position operation."""

    stepper_id: int
    position: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepperPositionResponse:
        """Parse from dict."""
        return cls(
            stepper_id=data.get("stepper_id", 0),
            position=data.get("position", 0),
        )


# =============================================================================
# IMU Responses
# =============================================================================

@dataclass(frozen=True, slots=True)
class ImuReadResponse:
    """Response from an IMU read operation."""

    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImuReadResponse:
        """Parse from dict."""
        return cls(
            pitch=data.get("pitch", 0.0),
            roll=data.get("roll", 0.0),
            yaw=data.get("yaw", 0.0),
            accel_x=data.get("accel_x", data.get("ax", 0.0)),
            accel_y=data.get("accel_y", data.get("ay", 0.0)),
            accel_z=data.get("accel_z", data.get("az", 0.0)),
            gyro_x=data.get("gyro_x", data.get("gx", 0.0)),
            gyro_y=data.get("gyro_y", data.get("gy", 0.0)),
            gyro_z=data.get("gyro_z", data.get("gz", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class ImuCalibrateResponse:
    """Response from an IMU calibrate operation."""

    samples: int
    delay_ms: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImuCalibrateResponse:
        """Parse from dict."""
        return cls(
            samples=data.get("samples", 100),
            delay_ms=data.get("delay_ms", 10),
        )


@dataclass(frozen=True, slots=True)
class ImuSetBiasResponse:
    """Response from an IMU set bias operation."""

    accel_bias: tuple[float, float, float]
    gyro_bias: tuple[float, float, float]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImuSetBiasResponse:
        """Parse from dict."""
        accel = data.get("accel_bias", [0.0, 0.0, 0.0])
        gyro = data.get("gyro_bias", [0.0, 0.0, 0.0])
        return cls(
            accel_bias=tuple(accel) if isinstance(accel, (list, tuple)) else (0.0, 0.0, 0.0),
            gyro_bias=tuple(gyro) if isinstance(gyro, (list, tuple)) else (0.0, 0.0, 0.0),
        )


# =============================================================================
# Ultrasonic Responses
# =============================================================================

@dataclass(frozen=True, slots=True)
class UltrasonicAttachResponse:
    """Response from an ultrasonic attach operation."""

    sensor_id: int
    trig_pin: int
    echo_pin: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UltrasonicAttachResponse:
        """Parse from dict."""
        return cls(
            sensor_id=data.get("sensor_id", 0),
            trig_pin=data.get("trig_pin", 0),
            echo_pin=data.get("echo_pin", 0),
        )


@dataclass(frozen=True, slots=True)
class UltrasonicDetachResponse:
    """Response from an ultrasonic detach operation."""

    sensor_id: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UltrasonicDetachResponse:
        """Parse from dict."""
        return cls(sensor_id=data.get("sensor_id", 0))


@dataclass(frozen=True, slots=True)
class UltrasonicReadResponse:
    """Response from an ultrasonic read operation."""

    sensor_id: int
    distance_cm: Optional[float] = None
    degraded: bool = False
    attached: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UltrasonicReadResponse:
        """Parse from dict."""
        return cls(
            sensor_id=data.get("sensor_id", 0),
            distance_cm=data.get("distance_cm"),
            degraded=data.get("degraded", False),
            attached=data.get("attached", True),
        )


# =============================================================================
# PWM Responses
# =============================================================================

@dataclass(frozen=True, slots=True)
class PwmSetResponse:
    """Response from a PWM set operation."""

    channel: int
    duty: float
    freq_hz: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PwmSetResponse:
        """Parse from dict."""
        return cls(
            channel=data.get("channel", 0),
            duty=data.get("duty", 0.0),
            freq_hz=data.get("freq_hz"),
        )


# =============================================================================
# Signal Responses
# =============================================================================

@dataclass(frozen=True, slots=True)
class SignalDefineResponse:
    """Response from a signal define operation."""

    signal_id: int
    name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignalDefineResponse:
        """Parse from dict."""
        return cls(
            signal_id=data.get("signal_id", 0),
            name=data.get("name", ""),
        )


@dataclass(frozen=True, slots=True)
class SignalDeleteResponse:
    """Response from a signal delete operation."""

    signal_id: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignalDeleteResponse:
        """Parse from dict."""
        return cls(signal_id=data.get("signal_id", 0))


@dataclass(frozen=True, slots=True)
class SignalSetResponse:
    """Response from a signal set operation."""

    signal_id: int
    value: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignalSetResponse:
        """Parse from dict."""
        return cls(
            signal_id=data.get("signal_id", 0),
            value=data.get("value", 0.0),
        )


@dataclass(frozen=True, slots=True)
class SignalGetResponse:
    """Response from a signal get operation."""

    signal_id: int
    value: float
    stale: bool = False  # True if value is from cache due to MCU timeout

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignalGetResponse:
        """Parse from dict."""
        return cls(
            signal_id=data.get("signal_id", 0),
            value=data.get("value", 0.0),
            stale=data.get("stale", False),
        )


@dataclass(frozen=True, slots=True)
class SignalListResponse:
    """Response from a signal list operation."""

    signals: tuple[int, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignalListResponse:
        """Parse from dict."""
        signals = data.get("signals", [])
        return cls(signals=tuple(signals) if isinstance(signals, (list, tuple)) else ())


# =============================================================================
# State Responses
# =============================================================================

@dataclass(frozen=True, slots=True)
class RobotStateResponse:
    """Response containing robot state."""

    state: str
    armed: bool = False
    active: bool = False
    estopped: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RobotStateResponse:
        """Parse from dict."""
        state = data.get("state", "UNKNOWN")
        return cls(
            state=state,
            armed=state in ("ARMED", "ACTIVE"),
            active=state == "ACTIVE",
            estopped=state == "ESTOPPED",
        )


# =============================================================================
# Control Graph Responses
# =============================================================================

@dataclass(frozen=True, slots=True)
class ControlGraphSlotStatus:
    """Status of a single control graph slot."""

    id: str
    enabled: bool
    last_value: float = 0.0
    rate_hz: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ControlGraphSlotStatus:
        """Parse from dict."""
        return cls(
            id=data.get("id", ""),
            enabled=data.get("enabled", False),
            last_value=data.get("last_value", 0.0),
            rate_hz=data.get("rate_hz"),
        )


@dataclass(frozen=True, slots=True)
class ControlGraphStatus:
    """Status of the control graph."""

    running: bool
    slot_count: int
    slots: tuple[ControlGraphSlotStatus, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ControlGraphStatus:
        """Parse from dict."""
        slots = tuple(
            ControlGraphSlotStatus.from_dict(s)
            for s in data.get("slots", [])
        )
        return cls(
            running=data.get("running", False),
            slot_count=data.get("slot_count", len(slots)),
            slots=slots,
        )


__all__ = [
    # GPIO
    "GpioReadResponse",
    "GpioWriteResponse",
    "GpioRegisterResponse",
    # Encoder
    "EncoderReadResponse",
    "EncoderAttachResponse",
    "EncoderResetResponse",
    "EncoderDetachResponse",
    # Servo
    "ServoAttachResponse",
    "ServoSetAngleResponse",
    "ServoDetachResponse",
    "ServoSetPulseResponse",
    # Motor
    "MotorSetSpeedResponse",
    "MotorAttachResponse",
    "MotorStopResponse",
    "MotorDetachResponse",
    # Stepper
    "StepperEnableResponse",
    "StepperMoveRelResponse",
    "StepperMoveDegResponse",
    "StepperMoveRevResponse",
    "StepperStopResponse",
    "StepperPositionResponse",
    # IMU
    "ImuReadResponse",
    "ImuCalibrateResponse",
    "ImuSetBiasResponse",
    # Ultrasonic
    "UltrasonicAttachResponse",
    "UltrasonicDetachResponse",
    "UltrasonicReadResponse",
    # PWM
    "PwmSetResponse",
    # Signal
    "SignalDefineResponse",
    "SignalDeleteResponse",
    "SignalSetResponse",
    "SignalGetResponse",
    "SignalListResponse",
    # State
    "RobotStateResponse",
    # Control Graph
    "ControlGraphSlotStatus",
    "ControlGraphStatus",
]
