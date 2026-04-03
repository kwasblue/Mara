# mara_host/services/control/encoder_service.py
"""
Encoder control service.

Provides high-level control for rotary encoders with position and velocity tracking.
"""

import math
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult
from mara_host.services.control.service_base import ConfigurableService
from mara_host.command.payloads import (
    EncoderAttachPayload,
    EncoderReadPayload,
    EncoderResetPayload,
    EncoderDetachPayload,
)
from mara_host.services.types import (
    EncoderAttachResponse,
    EncoderReadResponse,
    EncoderResetResponse,
    EncoderDetachResponse,
)

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class EncoderConfig:
    """Configuration for an encoder."""

    encoder_id: int
    pin_a: int = 0  # CLK/Phase A pin
    pin_b: int = 0  # DT/Phase B pin
    ppr: int = 11  # Pulses per revolution
    gear_ratio: float = 1.0  # Gear ratio (for geared motors)
    inverted: bool = False


@dataclass
class EncoderState:
    """Current state of an encoder."""

    encoder_id: int
    count: int = 0  # Raw encoder count
    velocity: float = 0.0  # Velocity in counts/second
    attached: bool = False


class EncoderService(ConfigurableService[EncoderConfig, EncoderState]):
    """
    Service for encoder control.

    Manages rotary encoders with attach/detach, read, and reset operations.

    Example:
        encoder_svc = EncoderService(client)

        # Attach encoder to pins
        await encoder_svc.attach(0, pin_a=34, pin_b=35, ppr=11)

        # Read encoder value
        result = await encoder_svc.read(0)

        # Reset count
        await encoder_svc.reset(0)

        # Detach when done
        await encoder_svc.detach(0)
    """

    config_class = EncoderConfig
    state_class = EncoderState
    id_field = "encoder_id"

    def configure(
        self,
        encoder_id: int,
        pin_a: int,
        pin_b: int,
        ppr: int = 11,
        gear_ratio: float = 1.0,
        inverted: bool = False,
    ) -> EncoderConfig:
        """
        Configure an encoder locally.

        Args:
            encoder_id: Encoder ID (0-3)
            pin_a: CLK/Phase A pin
            pin_b: DT/Phase B pin
            ppr: Pulses per revolution
            gear_ratio: Gear ratio for geared motors
            inverted: If True, invert direction

        Returns:
            EncoderConfig
        """
        config = EncoderConfig(
            encoder_id=encoder_id,
            pin_a=pin_a,
            pin_b=pin_b,
            ppr=ppr,
            gear_ratio=gear_ratio,
            inverted=inverted,
        )
        self._configs[encoder_id] = config
        return config

    def get_attached_encoders(self) -> list[int]:
        """Get list of attached encoder IDs."""
        return [eid for eid, state in self._states.items() if state.attached]

    def counts_to_radians(self, encoder_id: int, counts: int) -> float:
        """Convert encoder counts to radians."""
        config = self.get_config(encoder_id)
        counts_per_rev = config.ppr * 4 * config.gear_ratio  # Quadrature encoding
        return (counts / counts_per_rev) * 2 * math.pi

    def counts_to_degrees(self, encoder_id: int, counts: int) -> float:
        """Convert encoder counts to degrees."""
        config = self.get_config(encoder_id)
        counts_per_rev = config.ppr * 4 * config.gear_ratio
        return (counts / counts_per_rev) * 360.0

    async def attach(
        self,
        encoder_id: int,
        pin_a: int,
        pin_b: int,
        ppr: int = 11,
        gear_ratio: float = 1.0,
    ) -> ServiceResult:
        """
        Attach an encoder to GPIO pins.

        Args:
            encoder_id: Encoder ID (0-3)
            pin_a: CLK/Phase A pin
            pin_b: DT/Phase B pin
            ppr: Pulses per revolution
            gear_ratio: Gear ratio

        Returns:
            ServiceResult
        """
        payload = EncoderAttachPayload(
            encoder_id=encoder_id, pin_a=pin_a, pin_b=pin_b, ppr=ppr, gear_ratio=gear_ratio
        )
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            self.configure(encoder_id, pin_a, pin_b, ppr, gear_ratio)
            state = self.get_state(encoder_id)
            state.attached = True
            return ServiceResult.success(
                data=EncoderAttachResponse(encoder_id=encoder_id, pin_a=pin_a, pin_b=pin_b)
            )
        else:
            return ServiceResult.failure(error=error or f"Failed to attach encoder {encoder_id}")

    async def detach(self, encoder_id: int) -> ServiceResult:
        """
        Detach an encoder.

        Args:
            encoder_id: Encoder ID

        Returns:
            ServiceResult
        """
        payload = EncoderDetachPayload(encoder_id=encoder_id)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            state = self.get_state(encoder_id)
            state.attached = False
            return ServiceResult.success(data=EncoderDetachResponse(encoder_id=encoder_id))
        else:
            return ServiceResult.failure(error=error or f"Failed to detach encoder {encoder_id}")

    async def read(self, encoder_id: int) -> ServiceResult:
        """
        Request encoder reading from MCU.

        Note: The actual value comes via telemetry.

        Args:
            encoder_id: Encoder ID

        Returns:
            ServiceResult
        """
        result = await self._send_reliable_with_ack_payload(
            "CMD_ENCODER_READ",
            {"encoder_id": encoder_id},
            error_message=f"Failed to read encoder {encoder_id}",
        )

        if result.ok:
            data = result.data or {"encoder_id": encoder_id}
            state = self.get_state(encoder_id)
            if isinstance(data, dict) and "ticks" in data:
                state.count = int(data["ticks"])
            return ServiceResult.success(data=data)
        else:
            return result

    async def reset(self, encoder_id: int) -> ServiceResult:
        """
        Reset encoder count to zero.

        Args:
            encoder_id: Encoder ID

        Returns:
            ServiceResult
        """
        payload = EncoderResetPayload(encoder_id=encoder_id)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            state = self.get_state(encoder_id)
            state.count = 0
            return ServiceResult.success(data=EncoderResetResponse(encoder_id=encoder_id))
        else:
            return ServiceResult.failure(error=error or f"Failed to reset encoder {encoder_id}")

    async def detach_all(self) -> ServiceResult:
        """
        Detach all attached encoders.

        Returns:
            ServiceResult
        """
        errors = []
        for encoder_id in self.get_attached_encoders():
            result = await self.detach(encoder_id)
            if not result.ok:
                errors.append(f"Encoder {encoder_id}: {result.error}")

        if errors:
            return ServiceResult.failure(error="; ".join(errors))
        return ServiceResult.success()
