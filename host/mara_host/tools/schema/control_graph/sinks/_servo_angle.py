"""Servo-angle sink definition."""

from ..core import ParamDef, SinkDef

SINK = SinkDef(
    kind="servo_angle",
    description="Drive a servo target angle in degrees.",
    params=(
        ParamDef.int("servo_id", required=True, minimum=0, description="Logical servo identifier."),
    ),
    inputs=1,
    stateful=False,
    mcu_supported=True,
    requires=("servo",),
    tags=("actuator",),
    impl_key="sink.servo_angle",
)
