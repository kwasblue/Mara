# mara_host/services/control/wifi_service.py
"""
Wi-Fi control service.

Provides runtime STA join/disconnect/status commands while keeping
AP recovery available on the robot.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mara_host.core.result import ServiceResult
from mara_host.services.control.service_base import ConfigurableService

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


class WifiService(ConfigurableService[dict, dict]):
    """Service for runtime Wi-Fi control on the MCU."""

    def __init__(self, client: "MaraClient"):
        super().__init__(client)

    async def status(self) -> ServiceResult:
        """Get current Wi-Fi/AP status from the MCU."""
        return await self._send_reliable_with_ack_payload(
            "CMD_WIFI_STATUS",
            {},
            error_message="Failed to get Wi-Fi status",
            ack_timeout_s=0.25,
        )

    async def join(
        self,
        ssid: str,
        password: str,
        wait_for_connect: bool = True,
        timeout_ms: int = 10000,
    ) -> ServiceResult:
        """Attempt to join a STA network at runtime."""
        result = await self._send_reliable_with_ack_payload(
            "CMD_WIFI_JOIN",
            {
                "ssid": ssid,
                "password": password,
                "wait_for_connect": wait_for_connect,
                "timeout_ms": timeout_ms,
            },
            error_message=f"Failed to join Wi-Fi network {ssid}",
            ack_timeout_s=max(0.5, timeout_ms / 1000.0 + 0.5),
        )
        if result.ok:
            return ServiceResult.success(data=result.data)
        return result

    async def disconnect(self) -> ServiceResult:
        """Disconnect STA while leaving AP recovery intact."""
        return await self._send_reliable_with_ack_payload(
            "CMD_WIFI_DISCONNECT",
            {},
            error_message="Failed to disconnect Wi-Fi",
            ack_timeout_s=0.25,
        )

    async def scan(self) -> ServiceResult:
        """Scan for available Wi-Fi networks.

        Returns:
            ServiceResult with networks list in data["networks"]
        """
        return await self._send_reliable_with_ack_payload(
            "CMD_WIFI_SCAN",
            {},
            error_message="Failed to scan Wi-Fi networks",
            ack_timeout_s=5.0,  # Scanning can take a few seconds
        )
