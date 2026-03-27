"""Delta-gate transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="delta_gate",
    description="Emit a new value only when it changes by at least a threshold from the last emitted value.",
    params=(
        ParamDef.float(
            "threshold",
            required=True,
            minimum=0.0,
            default=0.0,
            description="Minimum absolute change required before a new value is emitted.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=True,
    mcu_supported=True,
    tags=("stateful", "gating"),
    impl_key="transform.delta_gate",
)
