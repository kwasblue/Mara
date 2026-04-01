# schema/gpio_channels/_led_status.py
"""LED status GPIO channel."""

from .core import GpioChannelDef

CHANNEL = GpioChannelDef.output(
    name="LED_STATUS",
    channel=0,
    pin_name="LED_STATUS",
    description="Status LED output",
)
