# schema/hardware/sensors/_lidar.py
"""LiDAR distance sensor definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ...telemetry.core import TelemetrySectionDef, FieldDef as TelemFieldDef
from ..core import SensorDef, GuiBlockDef, FirmwareHints, PythonHints

SENSOR = SensorDef(
    name="lidar",
    interface="uart",
    description="LiDAR time-of-flight distance sensor",
    gui=GuiBlockDef(
        label="LiDAR",
        color="#8B5CF6",
        outputs=(("dist", "DIST"),),
    ),
    commands={
        "CMD_LIDAR_ATTACH": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Attach/configure LiDAR sensor",
            payload={
                "sensor_id": CmdFieldDef(type="int", default=0),
            },
        ),
    },
    telemetry=TelemetrySectionDef(
        name="TELEM_LIDAR",
        section_id=0x03,
        description="LiDAR distance sensor",
        fields=(
            TelemFieldDef.uint8("online"),
            TelemFieldDef.uint8("ok"),
            TelemFieldDef.uint16("dist_mm", scale=0.001, description="Distance in meters"),
            TelemFieldDef.uint16("signal", description="Signal strength"),
        ),
    ),
    firmware=FirmwareHints(
        class_name="LidarSensor",
        feature_flag="HAS_LIDAR",
        capability="CAP_LIDAR",
        manager="LidarManager",
        handler="SensorHandler",
    ),
    python=PythonHints(
        api_class="Lidar",
        reading_class="LidarReading",
        telemetry_topic="telemetry.lidar",
    ),
)
