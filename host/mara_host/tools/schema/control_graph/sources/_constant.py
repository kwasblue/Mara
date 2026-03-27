"""Constant-value source definition."""

from ..core import ParamDef, SourceDef

SOURCE = SourceDef(
    kind="constant",
    description="Publish a constant scalar value each tick.",
    params=(
        ParamDef.float(
            "value",
            required=True,
            default=0.0,
            description="Constant scalar value to publish.",
        ),
    ),
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("utility",),
    impl_key="source.constant",
)
