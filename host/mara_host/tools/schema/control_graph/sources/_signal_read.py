"""Signal-read source definition - reads a signal bus signal as slot input."""

from ..core import ParamDef, SourceDef

SOURCE = SourceDef(
    kind="signal_read",
    description="Read a signal value from the signal bus as slot input. Enables cross-slot communication and feedback loops.",
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
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("routing", "signal_bus"),
    impl_key="source.signal_read",
)
