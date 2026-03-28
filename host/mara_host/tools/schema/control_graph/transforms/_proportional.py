"""Proportional (P) transform definition - alias for scale with control semantics."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="proportional",
    description="Proportional gain (P term). Multiplies input by gain factor.",
    params=(
        ParamDef.float(
            "gain",
            required=False,
            default=1.0,
            description="Proportional gain factor (Kp).",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("control", "math"),
    impl_key="transform.proportional",
)
