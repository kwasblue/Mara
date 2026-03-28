"""Pulse generator transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="pulse",
    description="Generate periodic pulses. Input is ignored.",
    params=(
        ParamDef.float(
            "interval_ms",
            required=True,
            default=1000.0,
            minimum=1.0,
            description="Time between pulse starts in milliseconds.",
            unit="ms",
        ),
        ParamDef.float(
            "duration_ms",
            required=True,
            default=100.0,
            minimum=1.0,
            description="Pulse duration in milliseconds.",
            unit="ms",
        ),
        ParamDef.float(
            "value",
            required=False,
            default=1.0,
            description="Output value during pulse (0 otherwise).",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=True,
    mcu_supported=True,
    tags=("generator", "periodic"),
    impl_key="transform.pulse",
)
