"""Derivative transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="derivative",
    description="Compute rate of change of input (dv/dt). Useful for predictive/damping control.",
    params=(
        ParamDef.float(
            "gain",
            required=False,
            default=1.0,
            description="Multiplier applied to the derivative output.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=True,
    mcu_supported=True,
    tags=("control", "math"),
    impl_key="transform.derivative",
)
