"""Map/remap transform definition."""

from ..core import ParamDef, TransformDef

TRANSFORM = TransformDef(
    kind="map",
    description="Linearly remap input from one range to another.",
    params=(
        ParamDef.float(
            "in_min",
            required=True,
            default=0.0,
            description="Input range minimum.",
        ),
        ParamDef.float(
            "in_max",
            required=True,
            default=1.0,
            description="Input range maximum.",
        ),
        ParamDef.float(
            "out_min",
            required=True,
            default=0.0,
            description="Output range minimum.",
        ),
        ParamDef.float(
            "out_max",
            required=True,
            default=1.0,
            description="Output range maximum.",
        ),
    ),
    inputs=1,
    outputs=1,
    stateful=False,
    mcu_supported=True,
    tags=("math", "scaling"),
    impl_key="transform.map",
)
