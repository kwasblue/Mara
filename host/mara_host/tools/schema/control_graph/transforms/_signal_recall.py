"""Signal-recall transform definition - reads a signal bus value mid-chain."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="signal_recall",
    description="Replace current value with a signal from the signal bus. Similar to recall but reads from signal bus instead of local taps.",
    params=(
        ParamDef.int(
            "signal_id",
            required=True,
            minimum=0,
            maximum=255,
            description="Signal ID to read from (must be pre-defined in signal bus).",
        ),
        ParamDef.float(
            "fallback",
            required=False,
            default=0.0,
            description="Value to use if signal is not defined or not yet written.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("routing", "signal_bus", "miso"),
    impl_key="transform.signal_recall",
)
