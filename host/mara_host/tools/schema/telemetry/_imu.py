# schema/telemetry/_imu.py
"""IMU telemetry section definition."""

from .core import TelemetrySectionDef, FieldDef

SECTION = TelemetrySectionDef(
    name="TELEM_IMU",
    section_id=0x01,
    description="IMU sensor data (accel, gyro, temp)",
    fields=(
        FieldDef.uint8("online"),
        FieldDef.uint8("ok"),
        FieldDef.int16("ax_mg", scale=0.001, description="Acceleration X in g"),
        FieldDef.int16("ay_mg", scale=0.001, description="Acceleration Y in g"),
        FieldDef.int16("az_mg", scale=0.001, description="Acceleration Z in g"),
        FieldDef.int16("gx_mdps", scale=0.001, description="Gyro X in deg/s"),
        FieldDef.int16("gy_mdps", scale=0.001, description="Gyro Y in deg/s"),
        FieldDef.int16("gz_mdps", scale=0.001, description="Gyro Z in deg/s"),
        FieldDef.int16("temp_c_centi", scale=0.01, description="Temperature in C"),
    ),
)
