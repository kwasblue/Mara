# schema/hardware/sensors/_encoder.py
"""Quadrature encoder sensor definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ...telemetry.core import TelemetrySectionDef, FieldDef as TelemFieldDef
from ..core import SensorDef, GuiBlockDef, FirmwareHints, PythonHints

SENSOR = SensorDef(
    name="encoder",
    interface="gpio",
    description="Quadrature rotary encoder",
    gui=GuiBlockDef(
        label="Encoder",
        color="#8B5CF6",
        outputs=(("A", "A"), ("B", "B")),
    ),
    commands={
        "CMD_ENCODER_ATTACH": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Attach quadrature encoder",
            payload={
                "encoder_id": CmdFieldDef(type="int", default=0),
                "pin_a": CmdFieldDef(type="int", required=True),
                "pin_b": CmdFieldDef(type="int", required=True),
            },
        ),
        "CMD_ENCODER_READ": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Read encoder tick count",
            payload={
                "encoder_id": CmdFieldDef(type="int", default=0),
            },
        ),
        "CMD_ENCODER_RESET": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Reset encoder count to zero",
            payload={
                "encoder_id": CmdFieldDef(type="int", default=0),
            },
        ),
    },
    telemetry=TelemetrySectionDef(
        name="TELEM_ENCODER0",
        section_id=0x04,
        description="Encoder 0 tick count",
        fields=(
            TelemFieldDef.int32("ticks", description="Encoder tick count"),
        ),
    ),
    firmware=FirmwareHints(
        class_name="EncoderSensor",
        feature_flag="HAS_ENCODER",
        capability="CAP_ENCODER",
        manager="EncoderManager",
        handler="SensorHandler",
        max_instances=4,
    ),
    python=PythonHints(
        api_class="Encoder",
        reading_class="EncoderReading",
        telemetry_topic="telemetry.encoder",
    ),
)
