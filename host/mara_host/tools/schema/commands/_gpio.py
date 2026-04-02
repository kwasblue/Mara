# schema/commands/_gpio.py
"""LED, GPIO, and PWM command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


GPIO_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_LED_ON": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Turn status LED on.",
        category="led",
        requires_arm=False,
        response_format="LED on",
    ),
    "CMD_LED_OFF": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Turn status LED off.",
        category="led",
        requires_arm=False,
        response_format="LED off",
    ),
    "CMD_GPIO_WRITE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set GPIO pin high or low.",
        payload={
            "channel": FieldDef(type="int", required=True, description="GPIO channel ID"),
            "value": FieldDef(type="int", required=True, description="0=low, 1=high"),
        },
        response_format="GPIO {channel} set to {value}",
    ),
    "CMD_GPIO_READ": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Read GPIO pin state.",
        payload={"channel": FieldDef(type="int", required=True, description="GPIO channel ID")},
        requires_arm=False,
    ),
    "CMD_GPIO_TOGGLE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Toggle GPIO pin state.",
        payload={"channel": FieldDef(type="int", required=True, description="GPIO channel ID")},
        response_format="GPIO {channel} toggled",
    ),
    "CMD_GPIO_REGISTER_CHANNEL": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Register a GPIO channel mapping a logical ID to a physical pin.",
        payload={
            "channel": FieldDef(type="int", required=True, description="Logical channel ID"),
            "pin": FieldDef(type="int", required=True, description="Physical GPIO pin number"),
            "mode": FieldDef(type="string", default="output", enum=("output", "input", "input_pullup"), description="Pin mode"),
        },
        requires_arm=False,
        response_format="GPIO {channel} registered on pin {pin} as {mode}",
    ),
    "CMD_PWM_SET": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set PWM duty cycle on a channel.",
        payload={
            "channel": FieldDef(type="int", required=True, description="PWM channel"),
            "duty": FieldDef(type="float", required=True, description="Duty cycle (0.0-1.0)"),
            "freq_hz": FieldDef(type="float", description="Frequency in Hz (optional)"),
        },
        category="pwm",
        response_format="PWM {channel} -> {duty:.0%}",
    ),
}

GPIO_COMMANDS: dict[str, dict] = export_command_dicts(GPIO_COMMAND_OBJECTS)
