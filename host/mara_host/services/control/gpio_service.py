# mara_host/services/control/gpio_service.py
"""
GPIO control service.

Provides high-level control for GPIO pins with state tracking.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult, send_command
from mara_host.services.control.service_base import ConfigurableService
from mara_host.command.payloads import (
    GpioRegisterChannelPayload,
    GpioWritePayload,
    GpioReadPayload,
    GpioTogglePayload,
    PwmSetPayload,
)
from mara_host.services.types import (
    GpioReadResponse,
    GpioWriteResponse,
    GpioRegisterResponse,
    PwmSetResponse,
)

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


class GpioService(ConfigurableService[GpioChannel, GpioChannel]):
    """
    Service for GPIO control.

    Manages GPIO channels with read/write/toggle operations
    and state tracking.

    Note: GPIO uses a single GpioChannel type for both config and state
    since they're combined in this service.

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

    config_class = GpioChannel
    state_class = GpioChannel
    id_field = "channel"

    def __init__(self, client: "MaraClient"):
        """
        Initialize GPIO service.

        Args:
            client: Connected MaraClient instance
        """
        super().__init__(client)
        # Alias for backwards compatibility
        self._channels = self._configs

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
        payload = GpioRegisterChannelPayload(channel=channel, pin=pin, mode=mode)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            self.configure(channel, pin=pin, mode=mode, label=label)
            return ServiceResult.success(
                data=GpioRegisterResponse(channel=channel, pin=pin, mode=mode)
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
            value: Value to write (0 or 1, or any truthy/falsy value)

        Returns:
            ServiceResult
        """
        # Normalize to 0 or 1 (accepts truthy/falsy values like True, 255, etc.)
        normalized_value = 1 if value else 0

        payload = GpioWritePayload(channel=channel, value=normalized_value)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            ch = self._channels.get(channel)
            if ch:
                ch.value = normalized_value
            return ServiceResult.success(data=GpioWriteResponse(channel=channel, value=normalized_value))
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
        result = await self._send_reliable_with_ack_payload(
            "CMD_GPIO_READ",
            {"channel": channel},
            error_message=f"Failed to read GPIO channel {channel}",
        )

        if result.ok:
            data = result.data or {"channel": channel}
            ch = self._channels.get(channel)
            if ch and isinstance(data, dict) and "value" in data:
                ch.value = int(data["value"])
            return ServiceResult.success(data=data)
        else:
            return result

    async def toggle(self, channel: int) -> ServiceResult:
        """
        Toggle a GPIO channel.

        Args:
            channel: GPIO channel number

        Returns:
            ServiceResult
        """
        payload = GpioTogglePayload(channel=channel)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            ch = self._channels.get(channel)
            new_value = 0
            if ch:
                ch.value = 1 - ch.value  # Toggle local state
                new_value = ch.value
            return ServiceResult.success(data=GpioWriteResponse(channel=channel, value=new_value))
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
        return await send_command(
            self.client, "CMD_LED_ON", {}, "Failed to turn LED on"
        )

    async def led_off(self) -> ServiceResult:
        """Turn status LED off."""
        return await send_command(
            self.client, "CMD_LED_OFF", {}, "Failed to turn LED off"
        )

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
        payload = PwmSetPayload(channel=channel, duty=duty, freq_hz=freq_hz)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            return ServiceResult.success(
                data=PwmSetResponse(channel=channel, duty=duty, freq_hz=int(freq_hz) if freq_hz else None)
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to set PWM on channel {channel}"
            )

    async def write_multiple(
        self,
        values: dict[int, int],
    ) -> ServiceResult:
        """
        Write multiple GPIO channels atomically in a single MCU batch.

        Uses CMD_BATCH_APPLY to commit all writes in one round-trip,
        avoiding inter-channel timing skew that would occur with
        sequential writes.

        Args:
            values: Dict of {channel: value}

        Returns:
            ServiceResult
        """
        if not values:
            return ServiceResult.success(data={"values": {}})

        # Build batch actions for CMD_BATCH_APPLY
        # Format: actions=[{cmd, args}, ...]
        actions = []
        normalized_values = {}
        for channel, value in values.items():
            normalized = 1 if value else 0
            normalized_values[channel] = normalized
            actions.append({
                "cmd": "CMD_GPIO_WRITE",
                "args": {"channel": channel, "value": normalized}
            })

        # Send as single batch command
        ok, error = await self.client.send_reliable(
            "CMD_BATCH_APPLY",
            {"actions": actions}
        )

        if ok:
            # Update local state for all channels
            for channel, normalized in normalized_values.items():
                ch = self._channels.get(channel)
                if ch:
                    ch.value = normalized
            return ServiceResult.success(data={"values": normalized_values})
        else:
            return ServiceResult.failure(
                error=error or f"Failed to write GPIO channels {list(values.keys())}"
            )
