"""Median filter transform definition."""

from ..core import TransformDef

TRANSFORM = TransformDef(
    kind="median",
    description="Rolling median filter (5-sample window). Rejects outlier spikes better than lowpass.",
    params=(),
    inputs=1,
    outputs=1,
    stateful=True,
    mcu_supported=True,
    tags=("filter",),
    impl_key="transform.median",
)
