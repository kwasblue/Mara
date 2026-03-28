# schema/commands/_gpio.py
"""LED, GPIO, and PWM command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


GPIO_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_LED_ON": CommandDef(kind="cmd", direction="host->mcu", description="Turn status LED on."),
    "CMD_LED_OFF": CommandDef(kind="cmd", direction="host->mcu", description="Turn status LED off."),
    "CMD_GPIO_WRITE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Write a digital value to a logical GPIO channel.",
        payload={
            "channel": FieldDef(type="int", required=True),
            "value": FieldDef(type="int", required=True),
        },
    ),
    "CMD_GPIO_READ": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Read a digital value from a logical GPIO channel.",
        payload={"channel": FieldDef(type="int", required=True)},
    ),
    "CMD_GPIO_TOGGLE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Toggle a logical GPIO channel.",
        payload={"channel": FieldDef(type="int", required=True)},
    ),
    "CMD_GPIO_REGISTER_CHANNEL": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Register or re-map a logical GPIO channel to a physical pin.",
        payload={
            "channel": FieldDef(type="int", required=True),
            "pin": FieldDef(type="int", required=True),
            "mode": FieldDef(type="string", default="output", enum=("output", "input", "input_pullup")),
        },
    ),
    "CMD_PWM_SET": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set PWM duty cycle for a logical channel.",
        payload={
            "channel": FieldDef(type="int", required=True),
            "duty": FieldDef(type="float", required=True),
            "freq_hz": FieldDef(type="float"),
        },
    ),
}

GPIO_COMMANDS: dict[str, dict] = export_command_dicts(GPIO_COMMAND_OBJECTS)
