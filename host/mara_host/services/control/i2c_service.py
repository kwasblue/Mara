"""
I2C control service.

Provides a minimal runtime I2C bus scan via the MCU.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mara_host.core.result import ServiceResult
from mara_host.services.control.service_base import ConfigurableService

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


class I2cService(ConfigurableService[dict, dict]):
    """Service for MCU-side I2C probing."""

    def __init__(self, client: "MaraClient"):
        super().__init__(client)

    async def scan(self) -> ServiceResult:
        """Scan the primary MCU I2C bus and return responding 7-bit addresses."""
        return await self._send_reliable_with_ack_payload(
            "CMD_I2C_SCAN",
            {},
            error_message="Failed to scan I2C bus",
            ack_timeout_s=0.5,
        )
