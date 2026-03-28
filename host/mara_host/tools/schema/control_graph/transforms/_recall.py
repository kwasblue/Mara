"""Recall transform definition - retrieves value from a named tap."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="recall",
    description="Retrieve value from a named tap. Replaces current value with tap value.",
    params=(
        ParamDef.string(
            "name",
            required=True,
            description="Name of the tap to recall from (must match a tap defined earlier in the slot).",
        ),
        ParamDef.float(
            "fallback",
            required=False,
            default=0.0,
            description="Value to use if tap not found.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("routing", "miso"),
    impl_key="transform.recall",
)
