"""Threshold (binary step) transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="threshold",
    description="Binary output based on cutoff value.",
    params=(
        ParamDef.float(
            "cutoff",
            required=True,
            default=0.5,
            description="Threshold cutoff value.",
        ),
        ParamDef.float(
            "output_low",
            required=False,
            default=0.0,
            description="Output value when input is below cutoff.",
        ),
        ParamDef.float(
            "output_high",
            required=False,
            default=1.0,
            description="Output value when input is at or above cutoff.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("logic",),
    impl_key="transform.threshold",
)
