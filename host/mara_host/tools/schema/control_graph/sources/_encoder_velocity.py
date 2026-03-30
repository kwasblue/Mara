"""Encoder velocity source definition - reads encoder velocity as slot input."""

from ..core import ParamDef, SourceDef

SOURCE = SourceDef(
    kind="encoder_velocity",
    description="Read encoder velocity (rad/s) as slot input. Provides feedback for velocity control loops.",
    params=(
        ParamDef.int(
            "encoder_id",
            required=True,
            minimum=0,
            maximum=7,
            description="Encoder channel ID (0-7).",
        ),
        ParamDef.float(
            "ticks_per_rad",
            required=False,
            default=1.0,
            minimum=0.001,
            description="Encoder ticks per radian. Used to convert tick rate to rad/s.",
        ),
        ParamDef.float(
            "fallback",
            required=False,
            default=0.0,
            description="Value to use if encoder is not available or not initialized.",
        ),
    ),
    outputs=1,
    stateful=True,  # Tracks previous count/time for velocity calculation
    mcu_supported=True,
    requires=("encoder",),
    tags=("sensor", "feedback", "control"),
    impl_key="source.encoder_velocity",
)
