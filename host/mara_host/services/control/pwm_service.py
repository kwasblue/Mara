# mara_host/services/control/pwm_service.py
"""
PWM control service.

Provides high-level control for PWM channels.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult
from mara_host.services.control.service_base import ConfigurableService

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class PwmConfig:
    """Configuration for a PWM channel."""

    channel: int
    frequency_hz: int = 1000  # PWM frequency
    resolution: int = 8  # Resolution in bits (8 = 256 levels)


@dataclass
class PwmState:
    """Current state of a PWM channel."""

    channel: int
    duty: float = 0.0  # Duty cycle (0.0 to 1.0)
    frequency_hz: int = 1000
    enabled: bool = False


class PwmService(ConfigurableService[PwmConfig, PwmState]):
    """
    Service for PWM control.

    Manages PWM channels with duty cycle and frequency control.

    Example:
        pwm_svc = PwmService(client)

        # Set PWM duty cycle
        await pwm_svc.set_duty(0, 0.5)  # 50% duty

        # Set with frequency
        await pwm_svc.set(0, duty=0.75, freq_hz=2000)

        # Stop PWM
        await pwm_svc.stop(0)
    """

    config_class = PwmConfig
    state_class = PwmState
    id_field = "channel"

    def configure(
        self,
        channel: int,
        frequency_hz: int = 1000,
        resolution: int = 8,
    ) -> PwmConfig:
        """
        Configure a PWM channel locally.

        Args:
            channel: PWM channel (0-15)
            frequency_hz: PWM frequency in Hz
            resolution: Resolution in bits

        Returns:
            PwmConfig
        """
        config = PwmConfig(
            channel=channel,
            frequency_hz=frequency_hz,
            resolution=resolution,
        )
        self._configs[channel] = config
        return config

    async def set(
        self,
        channel: int,
        duty: float,
        freq_hz: Optional[int] = None,
    ) -> ServiceResult:
        """
        Set PWM duty cycle and optionally frequency.

        Args:
            channel: PWM channel (0-15)
            duty: Duty cycle (0.0 to 1.0)
            freq_hz: Frequency in Hz (optional)

        Returns:
            ServiceResult
        """
        # Clamp duty cycle
        duty = max(0.0, min(1.0, duty))

        payload = {
            "channel": channel,
            "duty": duty,
        }
        if freq_hz is not None:
            payload["freq_hz"] = freq_hz

        ok, error = await self.client.send_reliable("CMD_PWM_SET", payload)

        if ok:
            state = self.get_state(channel)
            state.duty = duty
            state.enabled = duty > 0
            if freq_hz is not None:
                state.frequency_hz = freq_hz
            return ServiceResult.success(data=payload)
        else:
            return ServiceResult.failure(
                error=error or f"Failed to set PWM on channel {channel}"
            )

    async def set_duty(self, channel: int, duty: float) -> ServiceResult:
        """
        Set PWM duty cycle only.

        Args:
            channel: PWM channel
            duty: Duty cycle (0.0 to 1.0)

        Returns:
            ServiceResult
        """
        return await self.set(channel, duty)

    async def set_percent(self, channel: int, percent: float) -> ServiceResult:
        """
        Set PWM duty cycle as percentage.

        Args:
            channel: PWM channel
            percent: Duty cycle as percentage (0 to 100)

        Returns:
            ServiceResult
        """
        duty = max(0.0, min(100.0, percent)) / 100.0
        return await self.set(channel, duty)

    async def stop(self, channel: int) -> ServiceResult:
        """
        Stop PWM on a channel (set duty to 0).

        Args:
            channel: PWM channel

        Returns:
            ServiceResult
        """
        result = await self.set(channel, 0.0)
        if result.ok:
            state = self.get_state(channel)
            state.enabled = False
        return result

    async def stop_all(self) -> ServiceResult:
        """
        Stop all PWM channels.

        Returns:
            ServiceResult
        """
        errors = []
        for channel in list(self._states.keys()):
            result = await self.stop(channel)
            if not result.ok:
                errors.append(f"Channel {channel}: {result.error}")

        if errors:
            return ServiceResult.failure(error="; ".join(errors))
        return ServiceResult.success()
