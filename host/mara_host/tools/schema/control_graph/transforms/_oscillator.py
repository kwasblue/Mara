"""Oscillator (sine wave) transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="oscillator",
    description="Generate sine wave output. Input is ignored; output is offset + amplitude * sin(phase).",
    params=(
        ParamDef.float(
            "frequency",
            required=True,
            default=1.0,
            minimum=0.001,
            description="Oscillation frequency in Hz.",
            unit="Hz",
        ),
        ParamDef.float(
            "amplitude",
            required=False,
            default=1.0,
            description="Peak amplitude of the sine wave.",
        ),
        ParamDef.float(
            "offset",
            required=False,
            default=0.0,
            description="DC offset added to the sine wave.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=True,
    mcu_supported=True,
    tags=("generator", "periodic"),
    impl_key="transform.oscillator",
)
