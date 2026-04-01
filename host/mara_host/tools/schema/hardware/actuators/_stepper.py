# schema/hardware/actuators/_stepper.py
"""Stepper motor actuator definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ...telemetry.core import TelemetrySectionDef, FieldDef as TelemFieldDef
from ..core import ActuatorDef, GuiBlockDef, FirmwareHints, PythonHints

ACTUATOR = ActuatorDef(
    name="stepper",
    interface="gpio",
    description="Stepper motor with step/dir driver (A4988, DRV8825, TMC2209)",
    gui=GuiBlockDef(
        label="Stepper",
        color="#A855F7",
        inputs=(("step", "STEP"), ("dir", "DIR"), ("en", "EN")),
    ),
    commands={
        "CMD_STEPPER_ENABLE": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Enable or disable a stepper driver (via enable pin).",
            payload={
                "stepper_id": CmdFieldDef(type="int", required=True),
                "enable": CmdFieldDef(type="bool", default=True),
            },
        ),
        "CMD_STEPPER_MOVE_REL": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Move a stepper a relative number of steps.",
            payload={
                "stepper_id": CmdFieldDef(type="int", required=True),
                "steps": CmdFieldDef(type="int", required=True),
                "speed_rps": CmdFieldDef(
                    type="float",
                    default=1.0,
                    description="Speed in revolutions per second.",
                ),
            },
        ),
        "CMD_STEPPER_MOVE_DEG": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Move a stepper a relative number of degrees.",
            payload={
                "stepper_id": CmdFieldDef(type="int", required=True),
                "degrees": CmdFieldDef(type="float", required=True),
                "speed_rps": CmdFieldDef(
                    type="float",
                    default=1.0,
                    description="Speed in revolutions per second.",
                ),
            },
        ),
        "CMD_STEPPER_MOVE_REV": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Move a stepper a relative number of revolutions.",
            payload={
                "stepper_id": CmdFieldDef(type="int", required=True),
                "revolutions": CmdFieldDef(type="float", required=True),
                "speed_rps": CmdFieldDef(
                    type="float",
                    default=1.0,
                    description="Speed in revolutions per second.",
                ),
            },
        ),
        "CMD_STEPPER_STOP": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Immediately stop a stepper motor.",
            payload={
                "stepper_id": CmdFieldDef(type="int", required=True),
            },
        ),
        "CMD_STEPPER_GET_POSITION": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Get the current position of a stepper motor in steps.",
            payload={
                "stepper_id": CmdFieldDef(type="int", required=True),
            },
        ),
        "CMD_STEPPER_RESET_POSITION": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Reset the stepper position counter to zero.",
            payload={
                "stepper_id": CmdFieldDef(type="int", required=True),
            },
        ),
    },
    telemetry=TelemetrySectionDef(
        name="TELEM_STEPPER0",
        section_id=0x05,
        description="Stepper motor 0 state",
        fields=(
            TelemFieldDef.int8("motor_id"),
            TelemFieldDef.uint8("attached"),
            TelemFieldDef.uint8("enabled"),
            TelemFieldDef.uint8("moving"),
            TelemFieldDef.uint8("dir_forward"),
            TelemFieldDef.int32("last_cmd_steps", description="Last commanded steps"),
            TelemFieldDef.int16("speed_centi", scale=0.01, description="Speed"),
        ),
    ),
    firmware=FirmwareHints(
        class_name="StepperActuator",
        feature_flag="HAS_STEPPER",
        capability="CAP_STEPPER",
        manager="StepperManager",
        handler="ActuatorHandler",
        max_instances=4,
    ),
    python=PythonHints(
        api_class="Stepper",
        reading_class="StepperState",
        telemetry_topic="telemetry.stepper",
    ),
)
