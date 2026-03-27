"""Slew-rate limiter transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="slew_rate",
    description="Limit how quickly the output is allowed to change, in output units per second.",
    params=(
        ParamDef.float(
            "rate",
            required=True,
            minimum=0.0,
            default=0.0,
            unit="units/s",
            description="Maximum absolute output change per second.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=True,
    mcu_supported=True,
    tags=("stateful", "limiter"),
    impl_key="transform.slew_rate",
)
