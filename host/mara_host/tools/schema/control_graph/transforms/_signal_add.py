"""Signal-add transform definition - adds a signal bus value to current value."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="signal_add",
    description="Add a signal value from the signal bus to the current value. Useful for merging parallel slot outputs.",
    params=(
        ParamDef.int(
            "signal_id",
            required=True,
            minimum=0,
            maximum=255,
            description="Signal ID to read and add (must be pre-defined in signal bus).",
        ),
        ParamDef.float(
            "fallback",
            required=False,
            default=0.0,
            description="Value to add if signal is not defined or not yet written.",
        ),
        ParamDef.float(
            "scale",
            required=False,
            default=1.0,
            description="Scale factor applied to signal value before adding.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("routing", "signal_bus", "miso", "math"),
    impl_key="transform.signal_add",
)
