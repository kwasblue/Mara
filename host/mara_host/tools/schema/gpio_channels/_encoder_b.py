# schema/gpio_channels/_encoder_b.py
"""Encoder B GPIO channel."""

from .core import GpioChannelDef

CHANNEL = GpioChannelDef.input(
    name="ENC0_B",
    channel=7,
    pin_name="ENC0_B",
    description="Encoder 0 channel B input",
)
