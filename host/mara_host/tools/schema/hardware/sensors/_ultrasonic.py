# schema/hardware/sensors/_ultrasonic.py
"""Ultrasonic distance sensor definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ...telemetry.core import TelemetrySectionDef, FieldDef as TelemFieldDef
from ..core import SensorDef, GuiBlockDef, FirmwareHints, PythonHints

SENSOR = SensorDef(
    name="ultrasonic",
    interface="gpio",
    description="Ultrasonic distance sensor (HC-SR04 compatible)",
    gui=GuiBlockDef(
        label="Ultrasonic",
        color="#3B82F6",
        inputs=(("trig", "TRIG"),),
        outputs=(("echo", "ECHO"),),
    ),
    commands={
        "CMD_ULTRASONIC_ATTACH": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Attach/configure an ultrasonic sensor",
            payload={
                "sensor_id": CmdFieldDef(type="int", default=0),
            },
        ),
        "CMD_ULTRASONIC_READ": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Trigger a single ultrasonic distance measurement",
            payload={
                "sensor_id": CmdFieldDef(type="int", default=0),
            },
        ),
    },
    telemetry=TelemetrySectionDef(
        name="TELEM_ULTRASONIC",
        section_id=0x02,
        description="Ultrasonic distance sensor",
        fields=(
            TelemFieldDef.uint8("sensor_id"),
            TelemFieldDef.uint8("attached"),
            TelemFieldDef.uint8("ok"),
            TelemFieldDef.uint16("dist_mm", scale=0.1, description="Distance in cm"),
        ),
    ),
    firmware=FirmwareHints(
        class_name="UltrasonicSensor",
        feature_flag="HAS_ULTRASONIC",
        capability="CAP_ULTRASONIC",
        manager="UltrasonicManager",
        handler="SensorHandler",
        max_instances=4,
    ),
    python=PythonHints(
        api_class="Ultrasonic",
        reading_class="UltrasonicReading",
        telemetry_topic="telemetry.ultrasonic",
    ),
)
