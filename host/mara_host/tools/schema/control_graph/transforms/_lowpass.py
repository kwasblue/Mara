"""Low-pass transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="lowpass",
    description="First-order exponential smoothing filter.",
    params=(
        ParamDef.float(
            "alpha",
            required=True,
            minimum=0.0,
            maximum=1.0,
            default=0.5,
            description="Smoothing factor; higher tracks the input more aggressively.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=True,
    mcu_supported=True,
    tags=("filter",),
    impl_key="transform.lowpass",
)
