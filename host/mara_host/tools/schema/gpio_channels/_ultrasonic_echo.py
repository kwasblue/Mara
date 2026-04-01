# schema/gpio_channels/_ultrasonic_echo.py
"""Ultrasonic echo GPIO channel."""

from .core import GpioChannelDef

CHANNEL = GpioChannelDef.input(
    name="ULTRASONIC_ECHO",
    channel=2,
    pin_name="ULTRA0_ECHO",
    description="Ultrasonic echo input",
)
