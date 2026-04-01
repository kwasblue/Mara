# schema/hardware/sensors/_temp.py
"""Temperature sensor definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ...telemetry.core import TelemetrySectionDef, FieldDef as TelemFieldDef
from ..core import SensorDef, GuiBlockDef, FirmwareHints, PythonHints

SENSOR = SensorDef(
    name="temp",
    interface="i2c",
    description="I2C temperature sensor",
    gui=GuiBlockDef(
        label="Temperature",
        color="#F59E0B",
        outputs=(("temp", "TEMP"),),
    ),
    commands={
        "CMD_TEMP_ATTACH": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Attach a temperature sensor",
            payload={
                "sensor_id": CmdFieldDef(type="int", default=0),
                "i2c_addr": CmdFieldDef(type="int", default=0x48),
            },
        ),
        "CMD_TEMP_READ": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Read temperature from sensor",
            payload={
                "sensor_id": CmdFieldDef(type="int", default=0),
            },
        ),
    },
    telemetry=TelemetrySectionDef(
        name="TELEM_TEMP",
        section_id=0x08,
        description="Temperature sensor reading",
        fields=(
            TelemFieldDef.uint8("sensor_id"),
            TelemFieldDef.uint8("ok"),
            TelemFieldDef.int16("temp_centi", scale=0.01, description="Temperature in C"),
        ),
    ),
    firmware=FirmwareHints(
        class_name="TemperatureSensor",
        feature_flag="HAS_TEMP_SENSOR",
        capability="CAP_TEMP",
        manager="TemperatureManager",
        handler="SensorHandler",
        max_instances=4,
    ),
    python=PythonHints(
        api_class="Temperature",
        reading_class="TemperatureReading",
        telemetry_topic="telemetry.temp",
    ),
)
