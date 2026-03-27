"""DC-motor speed sink definition."""

from ..core import ParamDef, SinkDef

SINK = SinkDef(
    kind="motor_speed",
    description="Drive a DC motor speed command from a scalar signal.",
    params=(
        ParamDef.int("motor_id", required=True, minimum=0, description="Logical motor identifier."),
    ),
    inputs=1,
    stateful=False,
    mcu_supported=True,
    requires=("dc_motor",),
    tags=("actuator",),
    impl_key="sink.motor_speed",
)
