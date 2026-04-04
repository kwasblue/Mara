"""
Control graph building utilities.

This module provides typed building blocks for creating control graphs
in a type-safe, composable way.

Example usage:
    from mara_host.control_graph import (
        Graph, Slot,
        # Sources
        ImuAxis, SignalRead, EncoderVelocity, Constant,
        # Transforms
        Scale, Lowpass, Clamp, Error, Integrator, Derivative,
        # Sinks
        ServoAngle, SignalWrite, MotorSpeed,
        # Builders
        PIDConfig, build_pid_graph, build_simple_pid_graph,
    )

    # Build a simple balance controller
    graph = Graph(slots=[
        Slot(
            id="balance",
            source=ImuAxis(axis="pitch"),
            transforms=[
                Lowpass(alpha=0.3),
                Scale(factor=2.0),
                Clamp(min=-1.0, max=1.0),
            ],
            sink=ServoAngle(servo_id=0),
        ),
    ])

    # Or use the PID builder for velocity control
    graph = build_pid_graph(PIDConfig(
        motor_id=0,
        encoder_id=0,
        kp=1.0, ki=0.1, kd=0.01,
    ))
"""

from .nodes import *

# Re-export schema types
from mara_host.tools.schema.control_graph.schema import (
    ControlGraphConfig as Graph,
    GraphSlotConfig as Slot,
    GraphNodeConfig as Node,
    ControlGraphValidationError,
    normalize_graph_model,
    validate_signal_references,
)

# Re-export builders
from mara_host.tools.schema.control_graph.builders import (
    PIDConfig,
    build_pid_graph,
    build_simple_pid_graph,
    build_cascaded_pid_graph,
)

__all__ = [
    # Schema types
    "Graph",
    "Slot",
    "Node",
    "ControlGraphValidationError",
    "normalize_graph_model",
    "validate_signal_references",
    # PID builders
    "PIDConfig",
    "build_pid_graph",
    "build_simple_pid_graph",
    "build_cascaded_pid_graph",
]
