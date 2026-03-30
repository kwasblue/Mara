"""Control graph builders - helper functions to generate common graph patterns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schema import ControlGraphConfig, GraphNodeConfig, GraphSlotConfig, GRAPH_SCHEMA_VERSION


@dataclass
class PIDConfig:
    """Configuration for a PID velocity control loop."""

    motor_id: int
    encoder_id: int
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0

    # Anti-windup limits for integrator
    i_min: float = -100.0
    i_max: float = 100.0

    # Output limits
    output_min: float = -1.0
    output_max: float = 1.0

    # Encoder configuration
    ticks_per_rad: float = 1.0

    # Signal IDs (auto-assigned if not specified)
    target_signal: int = 0
    feedback_signal: int = 1
    error_signal: int = 2
    p_signal: int = 3
    i_signal: int = 4
    d_signal: int = 5

    # Slot rate
    rate_hz: int = 100

    # Optional D-term lowpass filter
    d_lowpass_alpha: float | None = None

    # Prefix for slot IDs
    prefix: str = "pid"


def build_pid_graph(config: PIDConfig) -> ControlGraphConfig:
    """
    Generate a composable PID velocity control graph.

    Creates 6 slots:
    1. encoder_feedback - reads encoder velocity → feedback signal
    2. error_calc - computes target - feedback → error signal
    3. p_term - proportional: error * Kp → P signal
    4. i_term - integral: error integrated → I signal
    5. d_term - derivative: error rate of change → D signal
    6. pid_output - sums P+I+D, clamps, outputs to motor

    Args:
        config: PID configuration parameters

    Returns:
        ControlGraphConfig ready to upload
    """
    prefix = config.prefix

    slots = []

    # Slot 1: Encoder velocity → feedback signal
    slots.append(GraphSlotConfig(
        id=f"{prefix}_encoder",
        rate_hz=config.rate_hz,
        source=GraphNodeConfig(
            type="encoder_velocity",
            params={
                "encoder_id": config.encoder_id,
                "ticks_per_rad": config.ticks_per_rad,
            },
        ),
        sink=GraphNodeConfig(
            type="signal_write",
            params={"signal_id": config.feedback_signal},
        ),
    ))

    # Slot 2: Error = target - feedback
    slots.append(GraphSlotConfig(
        id=f"{prefix}_error",
        rate_hz=config.rate_hz,
        source=GraphNodeConfig(
            type="signal_read",
            params={"signal_id": config.target_signal},
        ),
        transforms=(
            GraphNodeConfig(
                type="error",
                params={"feedback_signal": config.feedback_signal},
            ),
        ),
        sink=GraphNodeConfig(
            type="signal_write",
            params={"signal_id": config.error_signal},
        ),
    ))

    # Slot 3: P term
    slots.append(GraphSlotConfig(
        id=f"{prefix}_p",
        rate_hz=config.rate_hz,
        source=GraphNodeConfig(
            type="signal_read",
            params={"signal_id": config.error_signal},
        ),
        transforms=(
            GraphNodeConfig(
                type="scale",
                params={"factor": config.kp},
            ),
        ),
        sink=GraphNodeConfig(
            type="signal_write",
            params={"signal_id": config.p_signal},
        ),
    ))

    # Slot 4: I term (with anti-windup)
    slots.append(GraphSlotConfig(
        id=f"{prefix}_i",
        rate_hz=config.rate_hz,
        source=GraphNodeConfig(
            type="signal_read",
            params={"signal_id": config.error_signal},
        ),
        transforms=(
            GraphNodeConfig(
                type="integrator",
                params={
                    "gain": config.ki,
                    "min": config.i_min,
                    "max": config.i_max,
                },
            ),
        ),
        sink=GraphNodeConfig(
            type="signal_write",
            params={"signal_id": config.i_signal},
        ),
    ))

    # Slot 5: D term (optionally with lowpass filter)
    d_transforms = []
    d_transforms.append(GraphNodeConfig(
        type="derivative",
        params={"gain": config.kd},
    ))
    if config.d_lowpass_alpha is not None:
        d_transforms.append(GraphNodeConfig(
            type="lowpass",
            params={"alpha": config.d_lowpass_alpha},
        ))

    slots.append(GraphSlotConfig(
        id=f"{prefix}_d",
        rate_hz=config.rate_hz,
        source=GraphNodeConfig(
            type="signal_read",
            params={"signal_id": config.error_signal},
        ),
        transforms=tuple(d_transforms),
        sink=GraphNodeConfig(
            type="signal_write",
            params={"signal_id": config.d_signal},
        ),
    ))

    # Slot 6: Sum P+I+D → motor
    slots.append(GraphSlotConfig(
        id=f"{prefix}_output",
        rate_hz=config.rate_hz,
        source=GraphNodeConfig(
            type="signal_read",
            params={"signal_id": config.p_signal},
        ),
        transforms=(
            GraphNodeConfig(
                type="signal_add",
                params={"signal_id": config.i_signal},
            ),
            GraphNodeConfig(
                type="signal_add",
                params={"signal_id": config.d_signal},
            ),
            GraphNodeConfig(
                type="clamp",
                params={"min": config.output_min, "max": config.output_max},
            ),
        ),
        sink=GraphNodeConfig(
            type="motor_speed",
            params={"motor_id": config.motor_id},
        ),
    ))

    return ControlGraphConfig(
        schema_version=GRAPH_SCHEMA_VERSION,
        slots=tuple(slots),
    )


def build_simple_pid_graph(
    motor_id: int,
    encoder_id: int,
    kp: float = 1.0,
    ki: float = 0.0,
    kd: float = 0.0,
    *,
    ticks_per_rad: float = 1.0,
    output_min: float = -1.0,
    output_max: float = 1.0,
    rate_hz: int = 100,
) -> dict[str, Any]:
    """
    Convenience function to generate a PID graph as a dict.

    Args:
        motor_id: DC motor ID to control
        encoder_id: Encoder ID for velocity feedback
        kp: Proportional gain
        ki: Integral gain
        kd: Derivative gain
        ticks_per_rad: Encoder ticks per radian
        output_min: Minimum motor command
        output_max: Maximum motor command
        rate_hz: Control loop rate in Hz

    Returns:
        Graph config dict ready for upload

    Example:
        >>> graph = build_simple_pid_graph(motor_id=0, encoder_id=0, kp=1.0, ki=0.1, kd=0.01)
        >>> await control_graph_service.apply(graph)
    """
    config = PIDConfig(
        motor_id=motor_id,
        encoder_id=encoder_id,
        kp=kp,
        ki=ki,
        kd=kd,
        ticks_per_rad=ticks_per_rad,
        output_min=output_min,
        output_max=output_max,
        rate_hz=rate_hz,
    )
    return build_pid_graph(config).to_dict()


def build_cascaded_pid_graph(
    outer_config: PIDConfig,
    inner_config: PIDConfig,
) -> ControlGraphConfig:
    """
    Generate a cascaded (nested) PID control graph.

    Outer loop output becomes inner loop setpoint.
    Common use: position (outer) → velocity (inner) → motor

    Args:
        outer_config: Outer loop PID config (e.g., position control)
        inner_config: Inner loop PID config (e.g., velocity control)

    Returns:
        ControlGraphConfig with both loops wired together
    """
    # Ensure inner loop reads from outer loop's output
    # Wire outer output signal to inner target signal
    inner_config.target_signal = outer_config.p_signal  # Use outer P+I+D sum location

    # Build both graphs
    outer_graph = build_pid_graph(outer_config)
    inner_graph = build_pid_graph(inner_config)

    # Modify outer to output to signal instead of motor
    outer_slots = list(outer_graph.slots)
    # Replace last slot's sink to write to inner's target signal
    last_slot = outer_slots[-1]
    outer_slots[-1] = GraphSlotConfig(
        id=last_slot.id,
        rate_hz=last_slot.rate_hz,
        source=last_slot.source,
        transforms=last_slot.transforms[:-1],  # Remove clamp, inner will clamp
        sink=GraphNodeConfig(
            type="signal_write",
            params={"signal_id": inner_config.target_signal},
        ),
    )

    # Combine slots
    all_slots = tuple(outer_slots) + inner_graph.slots

    return ControlGraphConfig(
        schema_version=GRAPH_SCHEMA_VERSION,
        slots=all_slots,
    )
