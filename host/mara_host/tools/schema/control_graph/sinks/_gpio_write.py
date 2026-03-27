"""GPIO-write sink definition."""

from ..core import ParamDef, SinkDef

SINK = SinkDef(
    kind="gpio_write",
    description="Drive a logical GPIO output from a scalar signal.",
    params=(
        ParamDef.int("channel", required=True, minimum=0, description="Logical GPIO channel."),
    ),
    inputs=1,
    stateful=False,
    mcu_supported=True,
    requires=("gpio",),
    tags=("actuator",),
    impl_key="sink.gpio_write",
)
