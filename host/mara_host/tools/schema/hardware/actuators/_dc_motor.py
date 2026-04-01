# schema/hardware/actuators/_dc_motor.py
"""DC motor actuator definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ...telemetry.core import TelemetrySectionDef, FieldDef as TelemFieldDef
from ..core import ActuatorDef, GuiBlockDef, FirmwareHints, PythonHints

ACTUATOR = ActuatorDef(
    name="dc_motor",
    interface="pwm",
    description="Brushed DC motor with H-bridge driver",
    gui=GuiBlockDef(
        label="DC Motor",
        color="#F97316",
        inputs=(("pwm", "PWM"), ("dir", "DIR")),
        outputs=(("enc", "ENC"),),
    ),
    commands={
        "CMD_DC_SET_SPEED": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Set DC motor speed and direction for a given motor ID.",
            payload={
                "motor_id": CmdFieldDef(
                    type="int",
                    required=True,
                    description="Logical DC motor ID (0..3).",
                ),
                "speed": CmdFieldDef(
                    type="float",
                    required=True,
                    description="Normalized speed in [-1.0, 1.0]; sign = direction.",
                    minimum=-1.0,
                    maximum=1.0,
                ),
            },
        ),
        "CMD_DC_STOP": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Stop a DC motor (set speed to zero).",
            payload={
                "motor_id": CmdFieldDef(
                    type="int",
                    required=True,
                    description="Logical DC motor ID (0..3).",
                ),
            },
        ),
        "CMD_DC_VEL_PID_ENABLE": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Enable or disable closed-loop velocity PID control for a DC motor.",
            payload={
                "motor_id": CmdFieldDef(
                    type="int",
                    required=True,
                    description="Logical DC motor ID (0..3).",
                ),
                "enable": CmdFieldDef(
                    type="bool",
                    required=True,
                    description="True to enable velocity PID, False to disable.",
                ),
            },
        ),
        "CMD_DC_SET_VEL_TARGET": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Set desired angular velocity target for a DC motor's PID controller.",
            payload={
                "motor_id": CmdFieldDef(
                    type="int",
                    required=True,
                    description="Logical DC motor ID (0..3).",
                ),
                "omega": CmdFieldDef(
                    type="float",
                    required=True,
                    description="Target angular velocity in rad/s (sign indicates direction).",
                ),
            },
        ),
        "CMD_DC_SET_VEL_GAINS": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Configure PID gains for DC motor velocity control.",
            payload={
                "motor_id": CmdFieldDef(
                    type="int",
                    required=True,
                    description="Logical DC motor ID (0..3).",
                ),
                "kp": CmdFieldDef(
                    type="float",
                    required=True,
                    description="Proportional gain for velocity PID.",
                ),
                "ki": CmdFieldDef(
                    type="float",
                    required=True,
                    description="Integral gain for velocity PID.",
                ),
                "kd": CmdFieldDef(
                    type="float",
                    required=True,
                    description="Derivative gain for velocity PID.",
                ),
            },
        ),
    },
    telemetry=TelemetrySectionDef(
        name="TELEM_DC_MOTOR0",
        section_id=0x06,
        description="DC motor 0 state",
        fields=(
            TelemFieldDef.uint8("attached"),
            TelemFieldDef.int16("speed_centi", scale=0.01, description="Speed (-1.0 to 1.0)"),
        ),
    ),
    firmware=FirmwareHints(
        class_name="DcMotorActuator",
        feature_flag="HAS_DC_MOTOR",
        capability="CAP_DC_MOTOR",
        manager="DcMotorManager",
        handler="ActuatorHandler",
        max_instances=4,
    ),
    python=PythonHints(
        api_class="DcMotor",
        reading_class="DcMotorState",
        telemetry_topic="telemetry.dc_motor",
    ),
)
