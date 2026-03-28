"""Absolute value transform definition."""

from ..core import TransformDef

TRANSFORM = TransformDef(
    kind="abs",
    description="Output absolute value of input.",
    params=(),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("math",),
    impl_key="transform.abs",
)
