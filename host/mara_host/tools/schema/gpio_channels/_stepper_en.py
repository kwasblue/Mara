# schema/gpio_channels/_stepper_en.py
"""Stepper enable GPIO channel."""

from .core import GpioChannelDef

CHANNEL = GpioChannelDef.output(
    name="STEPPER0_EN",
    channel=5,
    pin_name="STEPPER0_EN",
    description="Stepper motor 0 enable output",
)
