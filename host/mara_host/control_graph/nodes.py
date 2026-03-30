"""
AUTO-GENERATED FILE - DO NOT EDIT

Generated from mara_host.tools.schema.control_graph definitions.
Run: python -m mara_host.tools.gen_control_graph_types
"""

from __future__ import annotations
from typing import Any

SCHEMA_VERSION = 1


# =============================================================================
# Sources
# =============================================================================

class Constant:
    """Publish a constant scalar value each tick."""
    _kind = "constant"
    _category = "source"

    def __init__(self, value: float = 0.0):
        self.value = value

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "value": self.value
        }}

    def __repr__(self) -> str:
        return f"Constant(...)"


class EncoderVelocity:
    """Read encoder velocity (rad/s) as slot input. Provides feedback for velocity control loops."""
    _kind = "encoder_velocity"
    _category = "source"

    def __init__(self, encoder_id: int, ticks_per_rad: float = 1.0, fallback: float = 0.0):
        self.encoder_id = encoder_id
        self.ticks_per_rad = ticks_per_rad
        self.fallback = fallback

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "encoder_id": self.encoder_id,
            "ticks_per_rad": self.ticks_per_rad,
            "fallback": self.fallback
        }}

    def __repr__(self) -> str:
        return f"EncoderVelocity(...)"


class ImuAxis:
    """Read a derived orientation axis from the IMU."""
    _kind = "imu_axis"
    _category = "source"

    def __init__(self, axis: str):
        self.axis = axis

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "axis": self.axis
        }}

    def __repr__(self) -> str:
        return f"ImuAxis(...)"


class SignalRead:
    """Read a signal value from the signal bus as slot input. Enables cross-slot communication and feedback loops."""
    _kind = "signal_read"
    _category = "source"

    def __init__(self, signal_id: int, fallback: float = 0.0):
        self.signal_id = signal_id
        self.fallback = fallback

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "signal_id": self.signal_id,
            "fallback": self.fallback
        }}

    def __repr__(self) -> str:
        return f"SignalRead(...)"


# =============================================================================
# Transforms
# =============================================================================

class Abs:
    """Output absolute value of input."""
    _kind = "abs"
    _category = "transform"

    def __init__(self):
        pass

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {}}

    def __repr__(self) -> str:
        return f"Abs(...)"


class Clamp:
    """Clamp the input signal to a configured range."""
    _kind = "clamp"
    _category = "transform"

    def __init__(self, min: float = -1.0, max: float = 1.0):
        self.min = min
        self.max = max

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "min": self.min,
            "max": self.max
        }}

    def __repr__(self) -> str:
        return f"Clamp(...)"


class Deadband:
    """Suppress small input values around zero."""
    _kind = "deadband"
    _category = "transform"

    def __init__(self, threshold: float = 0.0):
        self.threshold = threshold

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "threshold": self.threshold
        }}

    def __repr__(self) -> str:
        return f"Deadband(...)"


class DeltaGate:
    """Emit a new value only when it changes by at least a threshold from the last emitted value."""
    _kind = "delta_gate"
    _category = "transform"

    def __init__(self, threshold: float = 0.0):
        self.threshold = threshold

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "threshold": self.threshold
        }}

    def __repr__(self) -> str:
        return f"DeltaGate(...)"


class Derivative:
    """Compute rate of change of input (dv/dt). Useful for predictive/damping control."""
    _kind = "derivative"
    _category = "transform"

    def __init__(self, gain: float = 1.0):
        self.gain = gain

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "gain": self.gain
        }}

    def __repr__(self) -> str:
        return f"Derivative(...)"


class Error:
    """Compute control error: current value (setpoint) minus feedback signal. Commonly used as first stage in PID loops."""
    _kind = "error"
    _category = "transform"

    def __init__(self, feedback_signal: int, fallback: float = 0.0):
        self.feedback_signal = feedback_signal
        self.fallback = fallback

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "feedback_signal": self.feedback_signal,
            "fallback": self.fallback
        }}

    def __repr__(self) -> str:
        return f"Error(...)"


class Hysteresis:
    """Schmitt trigger with separate on/off thresholds to prevent chattering."""
    _kind = "hysteresis"
    _category = "transform"

    def __init__(self, on_threshold: float = 0.5, off_threshold: float = 0.3):
        self.on_threshold = on_threshold
        self.off_threshold = off_threshold

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "on_threshold": self.on_threshold,
            "off_threshold": self.off_threshold
        }}

    def __repr__(self) -> str:
        return f"Hysteresis(...)"


class Integrator:
    """Accumulate input over time (integral). Includes anti-windup bounds."""
    _kind = "integrator"
    _category = "transform"

    def __init__(self, gain: float = 1.0, min: float = -1000.0, max: float = 1000.0):
        self.gain = gain
        self.min = min
        self.max = max

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "gain": self.gain,
            "min": self.min,
            "max": self.max
        }}

    def __repr__(self) -> str:
        return f"Integrator(...)"


class Lowpass:
    """First-order exponential smoothing filter."""
    _kind = "lowpass"
    _category = "transform"

    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "alpha": self.alpha
        }}

    def __repr__(self) -> str:
        return f"Lowpass(...)"


class Map:
    """Linearly remap input from one range to another."""
    _kind = "map"
    _category = "transform"

    def __init__(self, in_min: float = 0.0, in_max: float = 1.0, out_min: float = 0.0, out_max: float = 1.0):
        self.in_min = in_min
        self.in_max = in_max
        self.out_min = out_min
        self.out_max = out_max

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "in_min": self.in_min,
            "in_max": self.in_max,
            "out_min": self.out_min,
            "out_max": self.out_max
        }}

    def __repr__(self) -> str:
        return f"Map(...)"


class Median:
    """Rolling median filter (5-sample window). Rejects outlier spikes better than lowpass."""
    _kind = "median"
    _category = "transform"

    def __init__(self):
        pass

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {}}

    def __repr__(self) -> str:
        return f"Median(...)"


class Negate:
    """Flip the sign of the input value."""
    _kind = "negate"
    _category = "transform"

    def __init__(self):
        pass

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {}}

    def __repr__(self) -> str:
        return f"Negate(...)"


class Offset:
    """Add a constant offset to the input signal."""
    _kind = "offset"
    _category = "transform"

    def __init__(self, value: float = 0.0):
        self.value = value

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "value": self.value
        }}

    def __repr__(self) -> str:
        return f"Offset(...)"


class Oscillator:
    """Generate sine wave output. Input is ignored; output is offset + amplitude * sin(phase)."""
    _kind = "oscillator"
    _category = "transform"

    def __init__(self, frequency: float = 1.0, amplitude: float = 1.0, offset: float = 0.0):
        self.frequency = frequency
        self.amplitude = amplitude
        self.offset = offset

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "frequency": self.frequency,
            "amplitude": self.amplitude,
            "offset": self.offset
        }}

    def __repr__(self) -> str:
        return f"Oscillator(...)"


class Proportional:
    """Proportional gain (P term). Multiplies input by gain factor."""
    _kind = "proportional"
    _category = "transform"

    def __init__(self, gain: float = 1.0):
        self.gain = gain

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "gain": self.gain
        }}

    def __repr__(self) -> str:
        return f"Proportional(...)"


class Pulse:
    """Generate periodic pulses. Input is ignored."""
    _kind = "pulse"
    _category = "transform"

    def __init__(self, interval_ms: float = 1000.0, duration_ms: float = 100.0, value: float = 1.0):
        self.interval_ms = interval_ms
        self.duration_ms = duration_ms
        self.value = value

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "interval_ms": self.interval_ms,
            "duration_ms": self.duration_ms,
            "value": self.value
        }}

    def __repr__(self) -> str:
        return f"Pulse(...)"


class Recall:
    """Retrieve value from a named tap. Replaces current value with tap value."""
    _kind = "recall"
    _category = "transform"

    def __init__(self, name: str, fallback: float = 0.0):
        self.name = name
        self.fallback = fallback

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "name": self.name,
            "fallback": self.fallback
        }}

    def __repr__(self) -> str:
        return f"Recall(...)"


class Scale:
    """Multiply the input signal by a scalar factor."""
    _kind = "scale"
    _category = "transform"

    def __init__(self, factor: float = 1.0):
        self.factor = factor

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "factor": self.factor
        }}

    def __repr__(self) -> str:
        return f"Scale(...)"


class SignalAdd:
    """Add a signal value from the signal bus to the current value. Useful for merging parallel slot outputs."""
    _kind = "signal_add"
    _category = "transform"

    def __init__(self, signal_id: int, fallback: float = 0.0, scale: float = 1.0):
        self.signal_id = signal_id
        self.fallback = fallback
        self.scale = scale

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "signal_id": self.signal_id,
            "fallback": self.fallback,
            "scale": self.scale
        }}

    def __repr__(self) -> str:
        return f"SignalAdd(...)"


class SignalRecall:
    """Replace current value with a signal from the signal bus. Similar to recall but reads from signal bus instead of local taps."""
    _kind = "signal_recall"
    _category = "transform"

    def __init__(self, signal_id: int, fallback: float = 0.0):
        self.signal_id = signal_id
        self.fallback = fallback

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "signal_id": self.signal_id,
            "fallback": self.fallback
        }}

    def __repr__(self) -> str:
        return f"SignalRecall(...)"


class SignalSubtract:
    """Subtract a signal value from the current value. Result is: current - signal."""
    _kind = "signal_subtract"
    _category = "transform"

    def __init__(self, signal_id: int, fallback: float = 0.0):
        self.signal_id = signal_id
        self.fallback = fallback

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "signal_id": self.signal_id,
            "fallback": self.fallback
        }}

    def __repr__(self) -> str:
        return f"SignalSubtract(...)"


class SlewRate:
    """Limit how quickly the output is allowed to change, in output units per second."""
    _kind = "slew_rate"
    _category = "transform"

    def __init__(self, rate: float = 0.0):
        self.rate = rate

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "rate": self.rate
        }}

    def __repr__(self) -> str:
        return f"SlewRate(...)"


class Sum:
    """Sum values from multiple named taps. Enables MISO (multiple-input, single-output) patterns like PID."""
    _kind = "sum"
    _category = "transform"

    def __init__(self, inputs: list[str]):
        self.inputs = inputs

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "inputs": self.inputs
        }}

    def __repr__(self) -> str:
        return f"Sum(...)"


class Tap:
    """Store current value to a named tap for recall by other transforms. Passes value through unchanged."""
    _kind = "tap"
    _category = "transform"

    def __init__(self, name: str):
        self.name = name

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "name": self.name
        }}

    def __repr__(self) -> str:
        return f"Tap(...)"


class Threshold:
    """Binary output based on cutoff value."""
    _kind = "threshold"
    _category = "transform"

    def __init__(self, cutoff: float = 0.5, output_low: float = 0.0, output_high: float = 1.0):
        self.cutoff = cutoff
        self.output_low = output_low
        self.output_high = output_high

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "cutoff": self.cutoff,
            "output_low": self.output_low,
            "output_high": self.output_high
        }}

    def __repr__(self) -> str:
        return f"Threshold(...)"


class Toggle:
    """Flip output state each time input crosses threshold (rising edge)."""
    _kind = "toggle"
    _category = "transform"

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "threshold": self.threshold
        }}

    def __repr__(self) -> str:
        return f"Toggle(...)"


# =============================================================================
# Sinks
# =============================================================================

class GpioWrite:
    """Drive a logical GPIO output from a scalar signal."""
    _kind = "gpio_write"
    _category = "sink"

    def __init__(self, channel: int):
        self.channel = channel

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "channel": self.channel
        }}

    def __repr__(self) -> str:
        return f"GpioWrite(...)"


class MotorSpeed:
    """Drive a DC motor speed command from a scalar signal."""
    _kind = "motor_speed"
    _category = "sink"

    def __init__(self, motor_id: int):
        self.motor_id = motor_id

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "motor_id": self.motor_id
        }}

    def __repr__(self) -> str:
        return f"MotorSpeed(...)"


class PwmDuty:
    """Drive a PWM duty-cycle command from a scalar signal."""
    _kind = "pwm_duty"
    _category = "sink"

    def __init__(self, channel: int):
        self.channel = channel

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "channel": self.channel
        }}

    def __repr__(self) -> str:
        return f"PwmDuty(...)"


class ServoAngle:
    """Drive a servo target angle in degrees."""
    _kind = "servo_angle"
    _category = "sink"

    def __init__(self, servo_id: int):
        self.servo_id = servo_id

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "servo_id": self.servo_id
        }}

    def __repr__(self) -> str:
        return f"ServoAngle(...)"


class SignalWrite:
    """Write slot output value to a signal in the signal bus. Enables cross-slot communication."""
    _kind = "signal_write"
    _category = "sink"

    def __init__(self, signal_id: int):
        self.signal_id = signal_id

    def to_dict(self) -> dict:
        return {"type": self._kind, "params": {
            "signal_id": self.signal_id
        }}

    def __repr__(self) -> str:
        return f"SignalWrite(...)"


# =============================================================================
# Graph Structure
# =============================================================================

class Slot:
    """A control graph slot with source, transforms, and sink(s)."""

    def __init__(
        self,
        id: str,
        source,
        sink = None,
        sinks: list | None = None,
        transforms: list | None = None,
        rate_hz: int | None = None,
        enabled: bool = True,
    ):
        self.id = id
        self.source = source
        self.sink = sink
        self.sinks = sinks or []
        self.transforms = transforms or []
        self.rate_hz = rate_hz
        self.enabled = enabled

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "enabled": self.enabled,
            "source": self.source.to_dict(),
            "transforms": [t.to_dict() for t in self.transforms],
        }
        if self.rate_hz is not None:
            d["rate_hz"] = self.rate_hz
        if self.sink is not None:
            d["sink"] = self.sink.to_dict()
        elif self.sinks:
            d["sinks"] = [s.to_dict() for s in self.sinks]
        return d

    def __repr__(self) -> str:
        return f"Slot({self.id!r}, ...)"


class Graph:
    """A complete control graph configuration."""

    def __init__(self, slots: list[Slot]):
        self.slots = slots
        self.schema_version = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "slots": [s.to_dict() for s in self.slots],
        }

    def __repr__(self) -> str:
        return f"Graph({len(self.slots)} slots)"


# =============================================================================
# Exports
# =============================================================================

SOURCES = [

    "Constant",
    "EncoderVelocity",
    "ImuAxis",
    "SignalRead",
]

TRANSFORMS = [
    "Abs",
    "Clamp",
    "Deadband",
    "DeltaGate",
    "Derivative",
    "Error",
    "Hysteresis",
    "Integrator",
    "Lowpass",
    "Map",
    "Median",
    "Negate",
    "Offset",
    "Oscillator",
    "Proportional",
    "Pulse",
    "Recall",
    "Scale",
    "SignalAdd",
    "SignalRecall",
    "SignalSubtract",
    "SlewRate",
    "Sum",
    "Tap",
    "Threshold",
    "Toggle",
]

SINKS = [
    "GpioWrite",
    "MotorSpeed",
    "PwmDuty",
    "ServoAngle",
    "SignalWrite",
]

__all__ = [
    "Graph",
    "Slot",
    "SCHEMA_VERSION",
    "Constant",
    "EncoderVelocity",
    "ImuAxis",
    "SignalRead",
    "Abs",
    "Clamp",
    "Deadband",
    "DeltaGate",
    "Derivative",
    "Error",
    "Hysteresis",
    "Integrator",
    "Lowpass",
    "Map",
    "Median",
    "Negate",
    "Offset",
    "Oscillator",
    "Proportional",
    "Pulse",
    "Recall",
    "Scale",
    "SignalAdd",
    "SignalRecall",
    "SignalSubtract",
    "SlewRate",
    "Sum",
    "Tap",
    "Threshold",
    "Toggle",
    "GpioWrite",
    "MotorSpeed",
    "PwmDuty",
    "ServoAngle",
    "SignalWrite",
]