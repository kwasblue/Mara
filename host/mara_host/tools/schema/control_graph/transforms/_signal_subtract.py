"""Signal-subtract transform definition - subtracts a signal bus value from current value."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="signal_subtract",
    description="Subtract a signal value from the current value. Result is: current - signal.",
    params=(
        ParamDef.int(
            "signal_id",
            required=True,
            minimum=0,
            maximum=255,
            description="Signal ID to read and subtract (must be pre-defined in signal bus).",
        ),
        ParamDef.float(
            "fallback",
            required=False,
            default=0.0,
            description="Value to subtract if signal is not defined or not yet written.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("routing", "signal_bus", "math"),
    impl_key="transform.signal_subtract",
)
