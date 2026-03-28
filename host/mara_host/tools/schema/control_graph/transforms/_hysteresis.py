"""Hysteresis (Schmitt trigger) transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="hysteresis",
    description="Schmitt trigger with separate on/off thresholds to prevent chattering.",
    params=(
        ParamDef.float(
            "on_threshold",
            required=True,
            default=0.5,
            description="Threshold to turn on (input must exceed this to go high).",
        ),
        ParamDef.float(
            "off_threshold",
            required=True,
            default=0.3,
            description="Threshold to turn off (input must drop below this to go low).",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=True,
    mcu_supported=True,
    tags=("logic", "filter"),
    impl_key="transform.hysteresis",
)
