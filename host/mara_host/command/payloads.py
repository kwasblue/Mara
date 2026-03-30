"""
AUTO-GENERATED FILE - DO NOT EDIT

Generated from mara_host.tools.schema.commands definitions.
Run: python -m mara_host.tools.gen_command_payloads
"""

from __future__ import annotations
from typing import Any


# =============================================================================
# Safety Commands
# =============================================================================

class DcStopPayload:
    """Stop a DC motor (set speed to zero)."""
    _cmd = "CMD_DC_STOP"

    def __init__(self, motor_id: int):
        self.motor_id = motor_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "motor_id": self.motor_id
        }

    def __repr__(self) -> str:
        return f"DcStopPayload(...)"


class SafetySetRatePayload:
    """Set safety loop rate in Hz. Only allowed when IDLE."""
    _cmd = "CMD_SAFETY_SET_RATE"

    def __init__(self, hz: int):
        self.hz = hz

    def to_dict(self) -> dict[str, Any]:
        return {
            "hz": self.hz
        }

    def __repr__(self) -> str:
        return f"SafetySetRatePayload(...)"


class StepperStopPayload:
    """Immediately stop a stepper motor."""
    _cmd = "CMD_STEPPER_STOP"

    def __init__(self, stepper_id: int):
        self.stepper_id = stepper_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "stepper_id": self.stepper_id
        }

    def __repr__(self) -> str:
        return f"StepperStopPayload(...)"


# =============================================================================
# Motion Commands
# =============================================================================

class SetLogLevelPayload:
    """Set MCU logging verbosity level."""
    _cmd = "CMD_SET_LOG_LEVEL"

    def __init__(self, level: str = 'info'):
        self.level = level

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level
        }

    def __repr__(self) -> str:
        return f"SetLogLevelPayload(...)"


class SetVelPayload:
    """Set linear and angular velocity in robot frame."""
    _cmd = "CMD_SET_VEL"

    def __init__(self, vx: float, omega: float, frame: str = 'robot'):
        self.vx = vx
        self.omega = omega
        self.frame = frame

    def to_dict(self) -> dict[str, Any]:
        return {
            "vx": self.vx,
            "omega": self.omega,
            "frame": self.frame
        }

    def __repr__(self) -> str:
        return f"SetVelPayload(...)"


# =============================================================================
# Servo Commands
# =============================================================================

class ServoAttachPayload:
    """Attach a servo ID to a physical pin."""
    _cmd = "CMD_SERVO_ATTACH"

    def __init__(self, servo_id: int, channel: int, min_us: int = 1000, max_us: int = 2000):
        self.servo_id = servo_id
        self.channel = channel
        self.min_us = min_us
        self.max_us = max_us

    def to_dict(self) -> dict[str, Any]:
        return {
            "servo_id": self.servo_id,
            "channel": self.channel,
            "min_us": self.min_us,
            "max_us": self.max_us
        }

    def __repr__(self) -> str:
        return f"ServoAttachPayload(...)"


class ServoDetachPayload:
    """Detach a servo ID."""
    _cmd = "CMD_SERVO_DETACH"

    def __init__(self, servo_id: int):
        self.servo_id = servo_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "servo_id": self.servo_id
        }

    def __repr__(self) -> str:
        return f"ServoDetachPayload(...)"


class ServoSetAnglePayload:
    """Set servo angle in degrees."""
    _cmd = "CMD_SERVO_SET_ANGLE"

    def __init__(self, servo_id: int, angle_deg: float, duration_ms: int = 0):
        self.servo_id = servo_id
        self.angle_deg = angle_deg
        self.duration_ms = duration_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "servo_id": self.servo_id,
            "angle_deg": self.angle_deg,
            "duration_ms": self.duration_ms
        }

    def __repr__(self) -> str:
        return f"ServoSetAnglePayload(...)"


class ServoSetPulsePayload:
    """Set servo pulse width in microseconds."""
    _cmd = "CMD_SERVO_SET_PULSE"

    def __init__(self, servo_id: int, pulse_us: int):
        self.servo_id = servo_id
        self.pulse_us = pulse_us

    def to_dict(self) -> dict[str, Any]:
        return {
            "servo_id": self.servo_id,
            "pulse_us": self.pulse_us
        }

    def __repr__(self) -> str:
        return f"ServoSetPulsePayload(...)"


# =============================================================================
# Dc Motor Commands
# =============================================================================

class DcSetSpeedPayload:
    """Set DC motor speed and direction for a given motor ID."""
    _cmd = "CMD_DC_SET_SPEED"

    def __init__(self, motor_id: int, speed: float):
        self.motor_id = motor_id
        self.speed = speed

    def to_dict(self) -> dict[str, Any]:
        return {
            "motor_id": self.motor_id,
            "speed": self.speed
        }

    def __repr__(self) -> str:
        return f"DcSetSpeedPayload(...)"


class DcSetVelGainsPayload:
    """Configure PID gains for DC motor velocity control."""
    _cmd = "CMD_DC_SET_VEL_GAINS"

    def __init__(self, motor_id: int, kp: float, ki: float, kd: float):
        self.motor_id = motor_id
        self.kp = kp
        self.ki = ki
        self.kd = kd

    def to_dict(self) -> dict[str, Any]:
        return {
            "motor_id": self.motor_id,
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd
        }

    def __repr__(self) -> str:
        return f"DcSetVelGainsPayload(...)"


class DcSetVelTargetPayload:
    """Set desired angular velocity target for a DC motor's PID controller."""
    _cmd = "CMD_DC_SET_VEL_TARGET"

    def __init__(self, motor_id: int, omega: float):
        self.motor_id = motor_id
        self.omega = omega

    def to_dict(self) -> dict[str, Any]:
        return {
            "motor_id": self.motor_id,
            "omega": self.omega
        }

    def __repr__(self) -> str:
        return f"DcSetVelTargetPayload(...)"


class DcVelPidEnablePayload:
    """Enable or disable closed-loop velocity PID control for a DC motor."""
    _cmd = "CMD_DC_VEL_PID_ENABLE"

    def __init__(self, motor_id: int, enable: bool):
        self.motor_id = motor_id
        self.enable = enable

    def to_dict(self) -> dict[str, Any]:
        return {
            "motor_id": self.motor_id,
            "enable": self.enable
        }

    def __repr__(self) -> str:
        return f"DcVelPidEnablePayload(...)"


# =============================================================================
# Stepper Commands
# =============================================================================

class StepperEnablePayload:
    """Enable or disable a stepper driver (via enable pin)."""
    _cmd = "CMD_STEPPER_ENABLE"

    def __init__(self, stepper_id: int, enable: bool = True):
        self.stepper_id = stepper_id
        self.enable = enable

    def to_dict(self) -> dict[str, Any]:
        return {
            "stepper_id": self.stepper_id,
            "enable": self.enable
        }

    def __repr__(self) -> str:
        return f"StepperEnablePayload(...)"


class StepperGetPositionPayload:
    """Get the current position of a stepper motor in steps."""
    _cmd = "CMD_STEPPER_GET_POSITION"

    def __init__(self, stepper_id: int):
        self.stepper_id = stepper_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "stepper_id": self.stepper_id
        }

    def __repr__(self) -> str:
        return f"StepperGetPositionPayload(...)"


class StepperMoveDegPayload:
    """Move a stepper a relative number of degrees."""
    _cmd = "CMD_STEPPER_MOVE_DEG"

    def __init__(self, stepper_id: int, degrees: float, speed_rps: float = 1.0):
        self.stepper_id = stepper_id
        self.degrees = degrees
        self.speed_rps = speed_rps

    def to_dict(self) -> dict[str, Any]:
        return {
            "stepper_id": self.stepper_id,
            "degrees": self.degrees,
            "speed_rps": self.speed_rps
        }

    def __repr__(self) -> str:
        return f"StepperMoveDegPayload(...)"


class StepperMoveRelPayload:
    """Move a stepper a relative number of steps."""
    _cmd = "CMD_STEPPER_MOVE_REL"

    def __init__(self, stepper_id: int, steps: int, speed_rps: float = 1.0):
        self.stepper_id = stepper_id
        self.steps = steps
        self.speed_rps = speed_rps

    def to_dict(self) -> dict[str, Any]:
        return {
            "stepper_id": self.stepper_id,
            "steps": self.steps,
            "speed_rps": self.speed_rps
        }

    def __repr__(self) -> str:
        return f"StepperMoveRelPayload(...)"


class StepperMoveRevPayload:
    """Move a stepper a relative number of revolutions."""
    _cmd = "CMD_STEPPER_MOVE_REV"

    def __init__(self, stepper_id: int, revolutions: float, speed_rps: float = 1.0):
        self.stepper_id = stepper_id
        self.revolutions = revolutions
        self.speed_rps = speed_rps

    def to_dict(self) -> dict[str, Any]:
        return {
            "stepper_id": self.stepper_id,
            "revolutions": self.revolutions,
            "speed_rps": self.speed_rps
        }

    def __repr__(self) -> str:
        return f"StepperMoveRevPayload(...)"


class StepperResetPositionPayload:
    """Reset the stepper position counter to zero."""
    _cmd = "CMD_STEPPER_RESET_POSITION"

    def __init__(self, stepper_id: int):
        self.stepper_id = stepper_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "stepper_id": self.stepper_id
        }

    def __repr__(self) -> str:
        return f"StepperResetPositionPayload(...)"


# =============================================================================
# Gpio Commands
# =============================================================================

class GpioReadPayload:
    """Read a digital value from a logical GPIO channel."""
    _cmd = "CMD_GPIO_READ"

    def __init__(self, channel: int):
        self.channel = channel

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel
        }

    def __repr__(self) -> str:
        return f"GpioReadPayload(...)"


class GpioRegisterChannelPayload:
    """Register or re-map a logical GPIO channel to a physical pin."""
    _cmd = "CMD_GPIO_REGISTER_CHANNEL"

    def __init__(self, channel: int, pin: int, mode: str = 'output'):
        self.channel = channel
        self.pin = pin
        self.mode = mode

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "pin": self.pin,
            "mode": self.mode
        }

    def __repr__(self) -> str:
        return f"GpioRegisterChannelPayload(...)"


class GpioTogglePayload:
    """Toggle a logical GPIO channel."""
    _cmd = "CMD_GPIO_TOGGLE"

    def __init__(self, channel: int):
        self.channel = channel

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel
        }

    def __repr__(self) -> str:
        return f"GpioTogglePayload(...)"


class GpioWritePayload:
    """Write a digital value to a logical GPIO channel."""
    _cmd = "CMD_GPIO_WRITE"

    def __init__(self, channel: int, value: int):
        self.channel = channel
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "value": self.value
        }

    def __repr__(self) -> str:
        return f"GpioWritePayload(...)"


# =============================================================================
# Sensors Commands
# =============================================================================

class EncoderAttachPayload:
    """Attach/configure a quadrature encoder with runtime pins."""
    _cmd = "CMD_ENCODER_ATTACH"

    def __init__(self, pin_a: int, pin_b: int, encoder_id: int = 0, ppr: int = 11, gear_ratio: float = 1.0):
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.encoder_id = encoder_id
        self.ppr = ppr
        self.gear_ratio = gear_ratio

    def to_dict(self) -> dict[str, Any]:
        return {
            "encoder_id": self.encoder_id,
            "pin_a": self.pin_a,
            "pin_b": self.pin_b,
            "ppr": self.ppr,
            "gear_ratio": self.gear_ratio
        }

    def __repr__(self) -> str:
        return f"EncoderAttachPayload(...)"


class EncoderDetachPayload:
    """Detach an encoder and free its resources."""
    _cmd = "CMD_ENCODER_DETACH"

    def __init__(self, encoder_id: int):
        self.encoder_id = encoder_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "encoder_id": self.encoder_id
        }

    def __repr__(self) -> str:
        return f"EncoderDetachPayload(...)"


class EncoderReadPayload:
    """Request current tick count for a given encoder."""
    _cmd = "CMD_ENCODER_READ"

    def __init__(self, encoder_id: int = 0):
        self.encoder_id = encoder_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "encoder_id": self.encoder_id
        }

    def __repr__(self) -> str:
        return f"EncoderReadPayload(...)"


class EncoderResetPayload:
    """Reset the tick count for a given encoder back to zero."""
    _cmd = "CMD_ENCODER_RESET"

    def __init__(self, encoder_id: int = 0):
        self.encoder_id = encoder_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "encoder_id": self.encoder_id
        }

    def __repr__(self) -> str:
        return f"EncoderResetPayload(...)"


class ImuCalibratePayload:
    """Calibrate the IMU by collecting samples to compute bias offsets."""
    _cmd = "CMD_IMU_CALIBRATE"

    def __init__(self, samples: int = 100, delay_ms: int = 10):
        self.samples = samples
        self.delay_ms = delay_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "samples": self.samples,
            "delay_ms": self.delay_ms
        }

    def __repr__(self) -> str:
        return f"ImuCalibratePayload(...)"


class ImuSetBiasPayload:
    """Set IMU bias offsets directly."""
    _cmd = "CMD_IMU_SET_BIAS"

    def __init__(self, accel_bias: list, gyro_bias: list):
        self.accel_bias = accel_bias
        self.gyro_bias = gyro_bias

    def to_dict(self) -> dict[str, Any]:
        return {
            "accel_bias": self.accel_bias,
            "gyro_bias": self.gyro_bias
        }

    def __repr__(self) -> str:
        return f"ImuSetBiasPayload(...)"


# =============================================================================
# Telemetry Commands
# =============================================================================

class ObserverConfigPayload:
    """Configure a Luenberger state observer."""
    _cmd = "CMD_OBSERVER_CONFIG"

    def __init__(self, slot: int, num_states: int, num_outputs: int, input_ids: list, output_ids: list, estimate_ids: list, num_inputs: int = 1, rate_hz: int = 200):
        self.slot = slot
        self.num_states = num_states
        self.num_outputs = num_outputs
        self.input_ids = input_ids
        self.output_ids = output_ids
        self.estimate_ids = estimate_ids
        self.num_inputs = num_inputs
        self.rate_hz = rate_hz

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "num_states": self.num_states,
            "num_inputs": self.num_inputs,
            "num_outputs": self.num_outputs,
            "rate_hz": self.rate_hz,
            "input_ids": self.input_ids,
            "output_ids": self.output_ids,
            "estimate_ids": self.estimate_ids
        }

    def __repr__(self) -> str:
        return f"ObserverConfigPayload(...)"


class ObserverEnablePayload:
    """Enable or disable a configured observer."""
    _cmd = "CMD_OBSERVER_ENABLE"

    def __init__(self, slot: int, enable: bool):
        self.slot = slot
        self.enable = enable

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "enable": self.enable
        }

    def __repr__(self) -> str:
        return f"ObserverEnablePayload(...)"


class ObserverResetPayload:
    """Reset observer state estimate to zero."""
    _cmd = "CMD_OBSERVER_RESET"

    def __init__(self, slot: int):
        self.slot = slot

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot
        }

    def __repr__(self) -> str:
        return f"ObserverResetPayload(...)"


class ObserverSetParamPayload:
    """Set individual matrix element (e.g., 'A01', 'L10')."""
    _cmd = "CMD_OBSERVER_SET_PARAM"

    def __init__(self, slot: int, key: str, value: float):
        self.slot = slot
        self.key = key
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "key": self.key,
            "value": self.value
        }

    def __repr__(self) -> str:
        return f"ObserverSetParamPayload(...)"


class ObserverSetParamArrayPayload:
    """Set full matrix (A, B, C, or L) in row-major order."""
    _cmd = "CMD_OBSERVER_SET_PARAM_ARRAY"

    def __init__(self, slot: int, key: str, values: list):
        self.slot = slot
        self.key = key
        self.values = values

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "key": self.key,
            "values": self.values
        }

    def __repr__(self) -> str:
        return f"ObserverSetParamArrayPayload(...)"


class ObserverStatusPayload:
    """Get observer status and current state estimates."""
    _cmd = "CMD_OBSERVER_STATUS"

    def __init__(self, slot: int):
        self.slot = slot

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot
        }

    def __repr__(self) -> str:
        return f"ObserverStatusPayload(...)"


# =============================================================================
# Wifi Commands
# =============================================================================

class WifiJoinPayload:
    """Connect to a WiFi network."""
    _cmd = "CMD_WIFI_JOIN"

    def __init__(self, ssid: str, password: str | None = None):
        self.ssid = ssid
        self.password = password

    def to_dict(self) -> dict[str, Any]:
        return {
            "ssid": self.ssid,
            "password": self.password
        }

    def __repr__(self) -> str:
        return f"WifiJoinPayload(...)"


# =============================================================================
# Other Commands
# =============================================================================

class BatchApplyPayload:
    """Apply a staged batch of batchable commands at one control boundary with deterministic MCU family ordering."""
    _cmd = "CMD_BATCH_APPLY"

    def __init__(self, actions: list):
        self.actions = actions

    def to_dict(self) -> dict[str, Any]:
        return {
            "actions": self.actions
        }

    def __repr__(self) -> str:
        return f"BatchApplyPayload(...)"


class CtrlGraphEnablePayload:
    """Enable or disable all stored control-graph slots."""
    _cmd = "CMD_CTRL_GRAPH_ENABLE"

    def __init__(self, enable: bool):
        self.enable = enable

    def to_dict(self) -> dict[str, Any]:
        return {
            "enable": self.enable
        }

    def __repr__(self) -> str:
        return f"CtrlGraphEnablePayload(...)"


class CtrlGraphUploadPayload:
    """Upload a runtime control-graph config. First slice stores validated graph config on the MCU."""
    _cmd = "CMD_CTRL_GRAPH_UPLOAD"

    def __init__(self, graph: dict[str, Any]):
        self.graph = graph

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph": self.graph
        }

    def __repr__(self) -> str:
        return f"CtrlGraphUploadPayload(...)"


class CtrlSetRatePayload:
    """Set control loop rate in Hz. Only allowed when IDLE."""
    _cmd = "CMD_CTRL_SET_RATE"

    def __init__(self, hz: int):
        self.hz = hz

    def to_dict(self) -> dict[str, Any]:
        return {
            "hz": self.hz
        }

    def __repr__(self) -> str:
        return f"CtrlSetRatePayload(...)"


class CtrlSignalDefinePayload:
    """Define a new signal in the signal bus. Only allowed when IDLE."""
    _cmd = "CMD_CTRL_SIGNAL_DEFINE"

    def __init__(self, id: int, name: str, signal_kind: str, initial: float = 0.0):
        self.id = id
        self.name = name
        self.signal_kind = signal_kind
        self.initial = initial

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "signal_kind": self.signal_kind,
            "initial": self.initial
        }

    def __repr__(self) -> str:
        return f"CtrlSignalDefinePayload(...)"


class CtrlSignalDeletePayload:
    """Delete a signal from the signal bus."""
    _cmd = "CMD_CTRL_SIGNAL_DELETE"

    def __init__(self, id: Any | None = None):
        self.id = id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id
        }

    def __repr__(self) -> str:
        return f"CtrlSignalDeletePayload(...)"


class CtrlSignalGetPayload:
    """Get a signal value from the signal bus."""
    _cmd = "CMD_CTRL_SIGNAL_GET"

    def __init__(self, id: int):
        self.id = id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id
        }

    def __repr__(self) -> str:
        return f"CtrlSignalGetPayload(...)"


class CtrlSignalSetPayload:
    """Set a signal value in the signal bus."""
    _cmd = "CMD_CTRL_SIGNAL_SET"

    def __init__(self, id: int, value: float):
        self.id = id
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "value": self.value
        }

    def __repr__(self) -> str:
        return f"CtrlSignalSetPayload(...)"


class CtrlSlotConfigPayload:
    """Configure a control slot with controller type and signal routing. Only allowed when IDLE."""
    _cmd = "CMD_CTRL_SLOT_CONFIG"

    def __init__(self, slot: int, controller_type: str, rate_hz: int = 100, ref_id: int | None = None, meas_id: int | None = None, out_id: int | None = None, num_states: int = 2, num_inputs: int = 1, state_ids: list | None = None, ref_ids: list | None = None, output_ids: list | None = None, require_armed: bool = True, require_active: bool = True):
        self.slot = slot
        self.controller_type = controller_type
        self.rate_hz = rate_hz
        self.ref_id = ref_id
        self.meas_id = meas_id
        self.out_id = out_id
        self.num_states = num_states
        self.num_inputs = num_inputs
        self.state_ids = state_ids
        self.ref_ids = ref_ids
        self.output_ids = output_ids
        self.require_armed = require_armed
        self.require_active = require_active

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "controller_type": self.controller_type,
            "rate_hz": self.rate_hz,
            "ref_id": self.ref_id,
            "meas_id": self.meas_id,
            "out_id": self.out_id,
            "num_states": self.num_states,
            "num_inputs": self.num_inputs,
            "state_ids": self.state_ids,
            "ref_ids": self.ref_ids,
            "output_ids": self.output_ids,
            "require_armed": self.require_armed,
            "require_active": self.require_active
        }

    def __repr__(self) -> str:
        return f"CtrlSlotConfigPayload(...)"


class CtrlSlotEnablePayload:
    """Enable or disable a configured control slot."""
    _cmd = "CMD_CTRL_SLOT_ENABLE"

    def __init__(self, slot: int, enable: bool):
        self.slot = slot
        self.enable = enable

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "enable": self.enable
        }

    def __repr__(self) -> str:
        return f"CtrlSlotEnablePayload(...)"


class CtrlSlotGetParamPayload:
    """Get a scalar parameter from a control slot's controller."""
    _cmd = "CMD_CTRL_SLOT_GET_PARAM"

    def __init__(self, slot: int, key: str):
        self.slot = slot
        self.key = key

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "key": self.key
        }

    def __repr__(self) -> str:
        return f"CtrlSlotGetParamPayload(...)"


class CtrlSlotResetPayload:
    """Reset a control slot's internal state (integrators, etc)."""
    _cmd = "CMD_CTRL_SLOT_RESET"

    def __init__(self, slot: int):
        self.slot = slot

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot
        }

    def __repr__(self) -> str:
        return f"CtrlSlotResetPayload(...)"


class CtrlSlotSetParamPayload:
    """Set a scalar parameter on a control slot's controller."""
    _cmd = "CMD_CTRL_SLOT_SET_PARAM"

    def __init__(self, slot: int, key: str, value: float):
        self.slot = slot
        self.key = key
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "key": self.key,
            "value": self.value
        }

    def __repr__(self) -> str:
        return f"CtrlSlotSetParamPayload(...)"


class CtrlSlotSetParamArrayPayload:
    """Set an array parameter on a control slot (e.g., gain matrix K for state-space)."""
    _cmd = "CMD_CTRL_SLOT_SET_PARAM_ARRAY"

    def __init__(self, slot: int, key: str, values: list):
        self.slot = slot
        self.key = key
        self.values = values

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "key": self.key,
            "values": self.values
        }

    def __repr__(self) -> str:
        return f"CtrlSlotSetParamArrayPayload(...)"


class CtrlSlotStatusPayload:
    """Get status of a control slot."""
    _cmd = "CMD_CTRL_SLOT_STATUS"

    def __init__(self, slot: int):
        self.slot = slot

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot
        }

    def __repr__(self) -> str:
        return f"CtrlSlotStatusPayload(...)"


class PwmSetPayload:
    """Set PWM duty cycle for a logical channel."""
    _cmd = "CMD_PWM_SET"

    def __init__(self, channel: int, duty: float, freq_hz: float | None = None):
        self.channel = channel
        self.duty = duty
        self.freq_hz = freq_hz

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "duty": self.duty,
            "freq_hz": self.freq_hz
        }

    def __repr__(self) -> str:
        return f"PwmSetPayload(...)"


class SetModePayload:
    """Set the high-level robot mode. Prefer ARM/ACTIVATE/DISARM/DEACTIVATE."""
    _cmd = "CMD_SET_MODE"

    def __init__(self, mode: str):
        self.mode = mode

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode
        }

    def __repr__(self) -> str:
        return f"SetModePayload(...)"


class TelemSetIntervalPayload:
    """Set telemetry publish interval in milliseconds (0 = disable)."""
    _cmd = "CMD_TELEM_SET_INTERVAL"

    def __init__(self, interval_ms: int = 100):
        self.interval_ms = interval_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "interval_ms": self.interval_ms
        }

    def __repr__(self) -> str:
        return f"TelemSetIntervalPayload(...)"


class TelemSetRatePayload:
    """Set telemetry loop rate in Hz. Only allowed when IDLE."""
    _cmd = "CMD_TELEM_SET_RATE"

    def __init__(self, hz: int):
        self.hz = hz

    def to_dict(self) -> dict[str, Any]:
        return {
            "hz": self.hz
        }

    def __repr__(self) -> str:
        return f"TelemSetRatePayload(...)"


class UltrasonicAttachPayload:
    """Attach/configure an ultrasonic sensor for the given logical sensor_id."""
    _cmd = "CMD_ULTRASONIC_ATTACH"

    def __init__(self, trig_pin: int, echo_pin: int, sensor_id: int = 0, max_distance_cm: float = 400.0):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.sensor_id = sensor_id
        self.max_distance_cm = max_distance_cm

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "trig_pin": self.trig_pin,
            "echo_pin": self.echo_pin,
            "max_distance_cm": self.max_distance_cm
        }

    def __repr__(self) -> str:
        return f"UltrasonicAttachPayload(...)"


class UltrasonicDetachPayload:
    """Detach an ultrasonic sensor and clear its cached state."""
    _cmd = "CMD_ULTRASONIC_DETACH"

    def __init__(self, sensor_id: int = 0):
        self.sensor_id = sensor_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensor_id": self.sensor_id
        }

    def __repr__(self) -> str:
        return f"UltrasonicDetachPayload(...)"


class UltrasonicReadPayload:
    """Trigger a single ultrasonic distance measurement."""
    _cmd = "CMD_ULTRASONIC_READ"

    def __init__(self, sensor_id: int = 0):
        self.sensor_id = sensor_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensor_id": self.sensor_id
        }

    def __repr__(self) -> str:
        return f"UltrasonicReadPayload(...)"


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "BatchApplyPayload",
    "CtrlGraphEnablePayload",
    "CtrlGraphUploadPayload",
    "CtrlSetRatePayload",
    "CtrlSignalDefinePayload",
    "CtrlSignalDeletePayload",
    "CtrlSignalGetPayload",
    "CtrlSignalSetPayload",
    "CtrlSlotConfigPayload",
    "CtrlSlotEnablePayload",
    "CtrlSlotGetParamPayload",
    "CtrlSlotResetPayload",
    "CtrlSlotSetParamArrayPayload",
    "CtrlSlotSetParamPayload",
    "CtrlSlotStatusPayload",
    "DcSetSpeedPayload",
    "DcSetVelGainsPayload",
    "DcSetVelTargetPayload",
    "DcStopPayload",
    "DcVelPidEnablePayload",
    "EncoderAttachPayload",
    "EncoderDetachPayload",
    "EncoderReadPayload",
    "EncoderResetPayload",
    "GpioReadPayload",
    "GpioRegisterChannelPayload",
    "GpioTogglePayload",
    "GpioWritePayload",
    "ImuCalibratePayload",
    "ImuSetBiasPayload",
    "ObserverConfigPayload",
    "ObserverEnablePayload",
    "ObserverResetPayload",
    "ObserverSetParamArrayPayload",
    "ObserverSetParamPayload",
    "ObserverStatusPayload",
    "PwmSetPayload",
    "SafetySetRatePayload",
    "ServoAttachPayload",
    "ServoDetachPayload",
    "ServoSetAnglePayload",
    "ServoSetPulsePayload",
    "SetLogLevelPayload",
    "SetModePayload",
    "SetVelPayload",
    "StepperEnablePayload",
    "StepperGetPositionPayload",
    "StepperMoveDegPayload",
    "StepperMoveRelPayload",
    "StepperMoveRevPayload",
    "StepperResetPositionPayload",
    "StepperStopPayload",
    "TelemSetIntervalPayload",
    "TelemSetRatePayload",
    "UltrasonicAttachPayload",
    "UltrasonicDetachPayload",
    "UltrasonicReadPayload",
    "WifiJoinPayload",
]