"""Signal-write sink definition - writes slot output to a signal bus signal."""

from ..core import ParamDef, SinkDef

SINK = SinkDef(
    kind="signal_write",
    description="Write slot output value to a signal in the signal bus. Enables cross-slot communication.",
    params=(
        ParamDef.int(
            "signal_id",
            required=True,
            minimum=0,
            maximum=255,
            description="Signal ID to write to (must be pre-defined in signal bus).",
        ),
    ),
    inputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("routing", "signal_bus"),
    impl_key="sink.signal_write",
)
