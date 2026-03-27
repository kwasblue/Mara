"""Scale transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="scale",
    description="Multiply the input signal by a scalar factor.",
    params=(
        ParamDef.float(
            "factor",
            required=True,
            default=1.0,
            description="Scalar multiplier applied to the input.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("math",),
    impl_key="transform.scale",
)
