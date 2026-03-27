"""IMU-derived axis source definition."""

from ..core import ParamDef, SourceDef

SOURCE = SourceDef(
    kind="imu_axis",
    description="Read a derived orientation axis from the IMU.",
    params=(
        ParamDef.enum_param(
            "axis",
            values=["pitch", "roll"],
            required=True,
            description="Derived tilt axis to publish.",
        ),
    ),
    outputs=1,
    stateful=False,
    mcu_supported=True,
    requires=("imu",),
    tags=("sensor", "orientation"),
    impl_key="source.imu_axis",
)
