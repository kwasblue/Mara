# mara_host/services/control/gpio_service.py
"""
GPIO control service.

Provides high-level control for GPIO pins with state tracking.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, TYPE_CHECKING

from mara_host.services.control.result import ServiceResult

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


class GpioMode(str, Enum):
    """GPIO pin modes."""

    OUTPUT = "output"
    INPUT = "input"
    INPUT_PULLUP = "input_pullup"
    INPUT_PULLDOWN = "input_pulldown"


@dataclass
class GpioChannel:
    """GPIO channel configuration and state."""

    channel: int
    pin: Optional[int] = None
    mode: GpioMode = GpioMode.OUTPUT
    value: int = 0
    label: str = ""


class GpioService:
    """
    Service for GPIO control.

    Manages GPIO channels with read/write/toggle operations
    and state tracking.

    Example:
        gpio = GpioService(client)

        # Register and configure a channel
        await gpio.register(0, pin=13, mode="output", label="LED")

        # Write value
        await gpio.write(0, 1)  # HIGH

        # Toggle
        await gpio.toggle(0)

        # Read
        result = await gpio.read(0)
        print(f"Value: {result.data['value']}")
    """

    def __init__(self, client: "MaraClient"):
        """
        Initialize GPIO service.

        Args:
            client: Connected MaraClient instance
        """
        self.client = client
        self._channels: dict[int, GpioChannel] = {}

    def configure(
        self,
        channel: int,
        pin: Optional[int] = None,
        mode: str = "output",
        label: str = "",
    ) -> GpioChannel:
        """
        Configure a GPIO channel locally.

        Args:
            channel: Logical channel number
            pin: Physical GPIO pin (optional, for tracking)
            mode: Pin mode (output, input, input_pullup)
            label: Human-readable label

        Returns:
            GpioChannel
        """
        gpio_mode = GpioMode(mode) if isinstance(mode, str) else mode
        ch = GpioChannel(
            channel=channel,
            pin=pin,
            mode=gpio_mode,
            label=label or f"GPIO{channel}",
        )
        self._channels[channel] = ch
        return ch

    def get_channel(self, channel: int) -> Optional[GpioChannel]:
        """Get channel configuration."""
        return self._channels.get(channel)

    def get_all_channels(self) -> dict[int, GpioChannel]:
        """Get all configured channels."""
        return self._channels.copy()

    async def register(
        self,
        channel: int,
        pin: int,
        mode: str = "output",
        label: str = "",
    ) -> ServiceResult:
        """
        Register a GPIO channel with the MCU.

        Args:
            channel: Logical channel number
            pin: Physical GPIO pin
            mode: Pin mode (output, input, input_pullup)
            label: Human-readable label

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_GPIO_REGISTER_CHANNEL",
            {
                "channel": channel,
                "pin": pin,
                "mode": mode,
            },
        )

        if ok:
            self.configure(channel, pin=pin, mode=mode, label=label)
            return ServiceResult.success(
                data={"channel": channel, "pin": pin, "mode": mode}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to register GPIO channel {channel}"
            )

    async def write(self, channel: int, value: int) -> ServiceResult:
        """
        Write a digital value to a GPIO channel.

        Args:
            channel: GPIO channel number
            value: Value to write (0 or 1)

        Returns:
            ServiceResult
        """
        value = 1 if value else 0

        ok, error = await self.client.send_reliable(
            "CMD_GPIO_WRITE",
            {"channel": channel, "value": value},
        )

        if ok:
            ch = self._channels.get(channel)
            if ch:
                ch.value = value
            return ServiceResult.success(data={"channel": channel, "value": value})
        else:
            return ServiceResult.failure(
                error=error or f"Failed to write GPIO channel {channel}"
            )

    async def read(self, channel: int) -> ServiceResult:
        """
        Read a digital value from a GPIO channel.

        Args:
            channel: GPIO channel number

        Returns:
            ServiceResult with value in data
        """
        ok, error = await self.client.send_reliable(
            "CMD_GPIO_READ",
            {"channel": channel},
        )

        if ok:
            # Value should be in the response
            # For now, we return success without value
            # The actual value comes from MCU response
            return ServiceResult.success(data={"channel": channel})
        else:
            return ServiceResult.failure(
                error=error or f"Failed to read GPIO channel {channel}"
            )

    async def toggle(self, channel: int) -> ServiceResult:
        """
        Toggle a GPIO channel.

        Args:
            channel: GPIO channel number

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_GPIO_TOGGLE",
            {"channel": channel},
        )

        if ok:
            ch = self._channels.get(channel)
            if ch:
                ch.value = 1 - ch.value  # Toggle local state
            return ServiceResult.success(data={"channel": channel})
        else:
            return ServiceResult.failure(
                error=error or f"Failed to toggle GPIO channel {channel}"
            )

    async def high(self, channel: int) -> ServiceResult:
        """Set GPIO channel HIGH."""
        return await self.write(channel, 1)

    async def low(self, channel: int) -> ServiceResult:
        """Set GPIO channel LOW."""
        return await self.write(channel, 0)

    async def led_on(self) -> ServiceResult:
        """Turn status LED on."""
        ok, error = await self.client.send_reliable("CMD_LED_ON", {})
        if ok:
            return ServiceResult.success()
        return ServiceResult.failure(error=error or "Failed to turn LED on")

    async def led_off(self) -> ServiceResult:
        """Turn status LED off."""
        ok, error = await self.client.send_reliable("CMD_LED_OFF", {})
        if ok:
            return ServiceResult.success()
        return ServiceResult.failure(error=error or "Failed to turn LED off")

    async def set_pwm(
        self,
        channel: int,
        duty: float,
        freq_hz: Optional[float] = None,
    ) -> ServiceResult:
        """
        Set PWM duty cycle on a channel.

        Args:
            channel: GPIO channel number
            duty: Duty cycle (0.0 to 1.0)
            freq_hz: PWM frequency in Hz (optional)

        Returns:
            ServiceResult
        """
        payload = {"channel": channel, "duty": duty}
        if freq_hz is not None:
            payload["freq_hz"] = freq_hz

        ok, error = await self.client.send_reliable("CMD_PWM_SET", payload)

        if ok:
            return ServiceResult.success(data={"channel": channel, "duty": duty})
        else:
            return ServiceResult.failure(
                error=error or f"Failed to set PWM on channel {channel}"
            )

    async def write_multiple(
        self,
        values: dict[int, int],
    ) -> ServiceResult:
        """
        Write multiple GPIO channels.

        Args:
            values: Dict of {channel: value}

        Returns:
            ServiceResult
        """
        errors = []
        for channel, value in values.items():
            result = await self.write(channel, value)
            if not result.ok:
                errors.append(f"Channel {channel}: {result.error}")

        if errors:
            return ServiceResult.failure(error="; ".join(errors))
        return ServiceResult.success(data={"values": values})
