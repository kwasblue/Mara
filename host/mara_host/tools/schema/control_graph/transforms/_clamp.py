"""Clamp transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="clamp",
    description="Clamp the input signal to a configured range.",
    params=(
        ParamDef.float("min", required=True, default=-1.0, description="Lower bound."),
        ParamDef.float("max", required=True, default=1.0, description="Upper bound."),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("math", "safety"),
    impl_key="transform.clamp",
)
