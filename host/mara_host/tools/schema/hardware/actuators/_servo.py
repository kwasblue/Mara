# schema/hardware/actuators/_servo.py
"""Servo motor actuator definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ..core import ActuatorDef, GuiBlockDef, FirmwareHints, PythonHints

ACTUATOR = ActuatorDef(
    name="servo",
    interface="pwm",
    description="PWM servo motor (hobby servos, 50Hz)",
    gui=GuiBlockDef(
        label="Servo",
        color="#06B6D4",
        inputs=(("pwm", "PWM"),),
    ),
    commands={
        "CMD_SERVO_ATTACH": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Attach a servo ID to a physical pin.",
            payload={
                "servo_id": CmdFieldDef(type="int", required=True),
                "channel": CmdFieldDef(type="int", required=True),
                "min_us": CmdFieldDef(type="int", default=1000),
                "max_us": CmdFieldDef(type="int", default=2000),
            },
        ),
        "CMD_SERVO_DETACH": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Detach a servo ID.",
            payload={
                "servo_id": CmdFieldDef(type="int", required=True),
            },
        ),
        "CMD_SERVO_SET_ANGLE": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Set servo angle in degrees.",
            payload={
                "servo_id": CmdFieldDef(type="int", required=True),
                "angle_deg": CmdFieldDef(type="float", required=True),
                "duration_ms": CmdFieldDef(
                    type="int",
                    default=0,
                    description="Interpolation duration in milliseconds (0 = immediate).",
                ),
            },
        ),
        "CMD_SERVO_SET_PULSE": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Set servo pulse width in microseconds.",
            payload={
                "servo_id": CmdFieldDef(type="int", required=True),
                "pulse_us": CmdFieldDef(
                    type="int",
                    required=True,
                    description="Pulse width in microseconds.",
                ),
            },
        ),
    },
    telemetry=None,  # Servos typically don't report telemetry
    firmware=FirmwareHints(
        class_name="ServoActuator",
        feature_flag="HAS_SERVO",
        capability="CAP_SERVO",
        manager="ServoManager",
        handler="ActuatorHandler",
        max_instances=16,
    ),
    python=PythonHints(
        api_class="Servo",
        reading_class="ServoState",
        telemetry_topic="telemetry.servo",
    ),
)
