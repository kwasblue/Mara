# schema/gpio_channels/_motor_left.py
"""Motor left IN1 GPIO channel."""

from .core import GpioChannelDef

CHANNEL = GpioChannelDef.output(
    name="MOTOR_LEFT_IN1",
    channel=3,
    pin_name="MOTOR_LEFT_IN1",
    description="DC motor left direction pin 1",
)
