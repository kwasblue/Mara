# schema/gpio_channels/_encoder.py
"""Encoder A GPIO channel."""

from .core import GpioChannelDef

CHANNEL = GpioChannelDef.input(
    name="ENC0_A",
    channel=6,
    pin_name="ENC0_A",
    description="Encoder 0 channel A input",
)
