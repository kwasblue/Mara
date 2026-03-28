"""Integrator transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="integrator",
    description="Accumulate input over time (integral). Includes anti-windup bounds.",
    params=(
        ParamDef.float(
            "gain",
            required=False,
            default=1.0,
            description="Multiplier applied to input before integrating.",
        ),
        ParamDef.float(
            "min",
            required=False,
            default=-1000.0,
            description="Anti-windup lower bound for accumulated value.",
        ),
        ParamDef.float(
            "max",
            required=False,
            default=1000.0,
            description="Anti-windup upper bound for accumulated value.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=True,
    mcu_supported=True,
    tags=("control", "math"),
    impl_key="transform.integrator",
)
