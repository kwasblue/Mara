"""Deadband transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="deadband",
    description="Suppress small input values around zero.",
    params=(
        ParamDef.float(
            "threshold",
            required=True,
            minimum=0.0,
            default=0.0,
            description="Magnitude below which the output is forced to zero.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("nonlinear",),
    impl_key="transform.deadband",
)
