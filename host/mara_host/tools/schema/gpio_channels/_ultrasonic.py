# schema/gpio_channels/_ultrasonic.py
"""Ultrasonic sensor GPIO channels."""

from .core import GpioChannelDef

# Note: Multiple channels can be in one file if they're related
# Discovery will look for CHANNEL, CHANNEL_1, CHANNEL_2, etc.
# For simplicity, we export only one per file

CHANNEL = GpioChannelDef.output(
    name="ULTRASONIC_TRIG",
    channel=1,
    pin_name="ULTRA0_TRIG",
    description="Ultrasonic trigger output",
)
