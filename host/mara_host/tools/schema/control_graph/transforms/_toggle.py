"""Toggle transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="toggle",
    description="Flip output state each time input crosses threshold (rising edge).",
    params=(
        ParamDef.float(
            "threshold",
            required=False,
            default=0.5,
            description="Threshold for detecting rising edge.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=True,
    mcu_supported=True,
    tags=("logic",),
    impl_key="transform.toggle",
)
