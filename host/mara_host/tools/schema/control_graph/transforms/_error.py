"""Error transform definition - computes control error (setpoint - feedback)."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="error",
    description="Compute control error: current value (setpoint) minus feedback signal. Commonly used as first stage in PID loops.",
    params=(
        ParamDef.int(
            "feedback_signal",
            required=True,
            minimum=0,
            maximum=255,
            description="Signal ID containing feedback/measurement value.",
        ),
        ParamDef.float(
            "fallback",
            required=False,
            default=0.0,
            description="Feedback value to use if signal is not defined.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("control", "signal_bus", "math"),
    impl_key="transform.error",
)
