# schema/gpio_channels/_motor_left_in2.py
"""Motor left IN2 GPIO channel."""

from .core import GpioChannelDef

CHANNEL = GpioChannelDef.output(
    name="MOTOR_LEFT_IN2",
    channel=4,
    pin_name="MOTOR_LEFT_IN2",
    description="DC motor left direction pin 2",
)
