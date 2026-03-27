"""Offset transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="offset",
    description="Add a constant offset to the input signal.",
    params=(
        ParamDef.float(
            "value",
            required=True,
            default=0.0,
            description="Constant value added to the input.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("math",),
    impl_key="transform.offset",
)
