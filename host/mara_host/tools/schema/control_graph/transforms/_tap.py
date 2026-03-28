"""Tap transform definition - stores intermediate value for later recall."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="tap",
    description="Store current value to a named tap for recall by other transforms. Passes value through unchanged.",
    params=(
        ParamDef.string(
            "name",
            required=True,
            description="Name of the tap (max 11 chars). Used by recall/sum to reference this value.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=True,
    mcu_supported=True,
    tags=("routing", "miso"),
    impl_key="transform.tap",
)
