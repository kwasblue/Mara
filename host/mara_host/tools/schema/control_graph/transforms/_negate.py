"""Negate transform definition."""

from ..core import TransformDef

TRANSFORM = TransformDef(
    kind="negate",
    description="Flip the sign of the input value.",
    params=(),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("math",),
    impl_key="transform.negate",
)
