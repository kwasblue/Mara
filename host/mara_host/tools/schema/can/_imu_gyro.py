# schema/can/_imu_gyro.py
"""IMU_GYRO CAN message definition."""

from .core import CanMessageDef, CanFieldDef

MESSAGE = CanMessageDef(
    name="IMU_GYRO",
    base_id="IMU_GYRO_BASE",
    direction="mcu->host",
    description="IMU gyroscope data (CAN-native, 8 bytes)",
    struct=(
        CanFieldDef.i16("gx", unit="mdps"),
        CanFieldDef.i16("gy", unit="mdps"),
        CanFieldDef.i16("gz", unit="mdps"),
        CanFieldDef.u16("timestamp", unit="ms"),
    ),
)
