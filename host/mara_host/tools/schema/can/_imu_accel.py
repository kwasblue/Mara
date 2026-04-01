# schema/can/_imu_accel.py
"""IMU_ACCEL CAN message definition."""

from .core import CanMessageDef, CanFieldDef

MESSAGE = CanMessageDef(
    name="IMU_ACCEL",
    base_id="IMU_ACCEL_BASE",
    direction="mcu->host",
    description="IMU accelerometer data (CAN-native, 8 bytes)",
    struct=(
        CanFieldDef.i16("ax", unit="mg"),
        CanFieldDef.i16("ay", unit="mg"),
        CanFieldDef.i16("az", unit="mg"),
        CanFieldDef.u16("timestamp", unit="ms"),
    ),
)
