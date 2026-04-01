# schema/hardware/sensors/_imu.py
"""IMU (Inertial Measurement Unit) sensor definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ...telemetry.core import TelemetrySectionDef, FieldDef as TelemFieldDef
from ..core import SensorDef, GuiBlockDef, FirmwareHints, PythonHints

SENSOR = SensorDef(
    name="imu",
    interface="i2c",
    description="Inertial Measurement Unit (accelerometer, gyroscope, temperature)",
    gui=GuiBlockDef(
        label="IMU",
        color="#22C55E",
        outputs=(("accel", "Accel"), ("gyro", "Gyro")),
    ),
    commands={
        "CMD_IMU_ATTACH": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Attach/configure IMU sensor",
            payload={
                "i2c_addr": CmdFieldDef(type="int", default=0x68),
            },
        ),
    },
    telemetry=TelemetrySectionDef(
        name="TELEM_IMU",
        section_id=0x01,
        description="IMU sensor data (accel, gyro, temp)",
        fields=(
            TelemFieldDef.uint8("online"),
            TelemFieldDef.uint8("ok"),
            TelemFieldDef.int16("ax_mg", scale=0.001, description="Acceleration X in g"),
            TelemFieldDef.int16("ay_mg", scale=0.001, description="Acceleration Y in g"),
            TelemFieldDef.int16("az_mg", scale=0.001, description="Acceleration Z in g"),
            TelemFieldDef.int16("gx_mdps", scale=0.001, description="Gyro X in deg/s"),
            TelemFieldDef.int16("gy_mdps", scale=0.001, description="Gyro Y in deg/s"),
            TelemFieldDef.int16("gz_mdps", scale=0.001, description="Gyro Z in deg/s"),
            TelemFieldDef.int16("temp_c_centi", scale=0.01, description="Temperature in C"),
        ),
    ),
    firmware=FirmwareHints(
        class_name="ImuSensor",
        feature_flag="HAS_IMU",
        capability="CAP_IMU",
        manager="ImuManager",
        handler="SensorHandler",
    ),
    python=PythonHints(
        api_class="Imu",
        reading_class="ImuReading",
        telemetry_topic="telemetry.imu",
    ),
)
