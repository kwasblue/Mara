# schema/hardware/sensors/_ir.py
"""Infrared sensor definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ...telemetry.core import TelemetrySectionDef, FieldDef as TelemFieldDef
from ..core import SensorDef, GuiBlockDef, FirmwareHints, PythonHints

SENSOR = SensorDef(
    name="ir",
    interface="adc",
    description="Infrared proximity/reflectance sensor",
    gui=GuiBlockDef(
        label="IR Sensor",
        color="#EF4444",
        outputs=(("out", "OUT"),),
    ),
    commands={
        "CMD_IR_ATTACH": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Attach IR sensor",
            payload={
                "sensor_id": CmdFieldDef(type="int", default=0),
                "adc_pin": CmdFieldDef(type="int", required=True),
            },
        ),
        "CMD_IR_READ": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Read IR sensor value",
            payload={
                "sensor_id": CmdFieldDef(type="int", default=0),
            },
        ),
    },
    telemetry=TelemetrySectionDef(
        name="TELEM_IR",
        section_id=0x09,
        description="IR sensor reading",
        fields=(
            TelemFieldDef.uint8("sensor_id"),
            TelemFieldDef.uint8("ok"),
            TelemFieldDef.uint16("value", description="Raw ADC value"),
        ),
    ),
    firmware=FirmwareHints(
        class_name="IrSensor",
        feature_flag="HAS_IR_SENSOR",
        capability="CAP_IR",
        manager="IrSensorManager",
        handler="SensorHandler",
        max_instances=8,
    ),
    python=PythonHints(
        api_class="IrSensor",
        reading_class="IrReading",
        telemetry_topic="telemetry.ir",
    ),
)
