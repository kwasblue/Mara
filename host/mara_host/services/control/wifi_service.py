# mara_host/services/control/wifi_service.py
"""
Wi-Fi control service.

Provides runtime STA join/disconnect/status commands while keeping
AP recovery available on the robot.

Security note: Wi-Fi passwords are sent to the MCU and may appear in debug logs
if payload logging is enabled. Ensure sensitive logs are protected in production.
"""

from __future__ import annotations

import asyncio
from typing import Any, TYPE_CHECKING

from mara_host.core.result import ServiceResult

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


class WifiService:
    """Service for runtime Wi-Fi control on the MCU.

    Note: This is a plain service (not ConfigurableService) since Wi-Fi
    connection state is managed by the MCU, not cached on the host.
    """

    def __init__(self, client: "MaraClient"):
        self.client = client

    async def _send_reliable_with_ack_payload(
        self,
        command: str,
        payload: dict,
        *,
        error_message: str,
        ack_timeout_s: float = 0.2,
    ) -> ServiceResult:
        """Send command and wait for ACK payload response."""
        loop = asyncio.get_running_loop()
        ack_future: asyncio.Future[Any] = loop.create_future()
        topic = f"cmd.{command}"

        def _handler(data: Any) -> None:
            if not ack_future.done():
                ack_future.set_result(data)

        self.client.bus.subscribe(topic, _handler)
        try:
            ok, error = await self.client.send_reliable(command, payload)
            if not ok:
                return ServiceResult.failure(error=error or error_message)

            try:
                ack_data = await asyncio.wait_for(ack_future, timeout=ack_timeout_s)
            except asyncio.TimeoutError:
                ack_data = None

            return ServiceResult.success(data=ack_data or payload)
        finally:
            self.client.bus.unsubscribe(topic, _handler)

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
