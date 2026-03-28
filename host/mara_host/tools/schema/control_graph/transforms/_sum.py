"""Sum transform definition - combines multiple tap values."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="sum",
    description="Sum values from multiple named taps. Enables MISO (multiple-input, single-output) patterns like PID.",
    params=(
        ParamDef.string_list(
            "inputs",
            required=True,
            description="List of tap names to sum together (max 4).",
        ),
    ),
    inputs=0,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("routing", "miso", "math"),
    impl_key="transform.sum",
)
