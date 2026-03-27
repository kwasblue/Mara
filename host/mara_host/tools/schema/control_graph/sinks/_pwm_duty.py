"""PWM-duty sink definition."""

from ..core import ParamDef, SinkDef

SINK = SinkDef(
    kind="pwm_duty",
    description="Drive a PWM duty-cycle command from a scalar signal.",
    params=(
        ParamDef.int("channel", required=True, minimum=0, description="Logical PWM channel identifier."),
    ),
    inputs=1,
    stateful=False,
    mcu_supported=True,
    requires=("pwm",),
    tags=("actuator",),
    impl_key="sink.pwm_duty",
)
