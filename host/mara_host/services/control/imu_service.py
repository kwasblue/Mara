# mara_host/services/control/imu_service.py
"""
IMU sensor service.

Provides high-level control for IMU (accelerometer/gyroscope) sensors.
"""

import asyncio
from dataclasses import asdict, dataclass
from typing import Any, Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult
from mara_host.command.payloads import (
    ImuCalibratePayload,
    ImuSetBiasPayload,
)
from mara_host.services.types import (
    ImuCalibrateResponse,
    ImuSetBiasResponse,
)

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class ImuReading:
    """IMU sensor reading."""

    online: bool = False

    # Accelerometer (sensor native g units from MCU snapshot)
    ax: float = 0.0
    ay: float = 0.0
    az: float = 0.0

    # Gyroscope (sensor native deg/s from MCU snapshot)
    gx: float = 0.0
    gy: float = 0.0
    gz: float = 0.0

    # Temperature (Celsius)
    temperature: float = 0.0


@dataclass
class ImuBias:
    """IMU bias correction values."""

    # Accelerometer bias
    ax: float = 0.0
    ay: float = 0.0
    az: float = 0.0

    # Gyroscope bias
    gx: float = 0.0
    gy: float = 0.0
    gz: float = 0.0


class ImuService:
    """
    Service for IMU sensor control.

    Manages IMU read, calibration, and bias operations.
    This is a plain class (not ConfigurableService) since there's
    typically only one IMU per robot.

    Example:
        imu_svc = ImuService(client)

        # Read IMU data
        result = await imu_svc.read()

        # Calibrate (robot must be stationary)
        await imu_svc.calibrate(samples=100)

        # Set manual bias
        await imu_svc.set_bias(ax=0.1, gx=-0.05)

        # Zero orientation
        await imu_svc.zero()
    """

    def __init__(self, client: "MaraClient"):
        """
        Initialize IMU service.

        Args:
            client: Connected MaraClient instance
        """
        self.client = client
        self._bias = ImuBias()
        self._last_reading: Optional[ImuReading] = None

    @property
    def bias(self) -> ImuBias:
        """Get current bias values."""
        return self._bias

    @property
    def last_reading(self) -> Optional[ImuReading]:
        """Get last IMU reading."""
        return self._last_reading

    async def _send_with_ack_payload(
        self,
        command: str,
        payload: dict,
        *,
        error_message: str,
        ack_timeout_s: float = 0.2,
    ) -> ServiceResult:
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
                ack_payload = await asyncio.wait_for(ack_future, timeout=ack_timeout_s)
            except asyncio.TimeoutError:
                ack_payload = None

            return ServiceResult.success(data=ack_payload or payload)
        finally:
            self.client.bus.unsubscribe(topic, _handler)

    async def read(self) -> ServiceResult:
        """
        Request an explicit IMU snapshot from the MCU.

        Returns:
            ServiceResult with snapshot data in ``data``.
        """
        result = await self._send_with_ack_payload(
            "CMD_IMU_READ",
            {},
            error_message="Failed to read IMU",
            ack_timeout_s=0.2,
        )

        if not result.ok:
            return result

        data = result.data or {}
        reading = ImuReading(
            online=bool(data.get("online", True)),
            ax=float(data.get("ax_g", 0.0)),
            ay=float(data.get("ay_g", 0.0)),
            az=float(data.get("az_g", 0.0)),
            gx=float(data.get("gx_dps", 0.0)),
            gy=float(data.get("gy_dps", 0.0)),
            gz=float(data.get("gz_dps", 0.0)),
            temperature=float(data.get("temp_c", 0.0)),
        )
        self._last_reading = reading
        payload = {
            **asdict(reading),
            "units": {
                "accel": "g",
                "gyro": "deg/s",
                "temperature": "C",
            },
        }
        return ServiceResult.success(data=payload)

    async def calibrate(
        self,
        samples: int = 100,
        delay_ms: int = 10,
    ) -> ServiceResult:
        """
        Calibrate IMU bias by averaging samples.

        The robot must be stationary on a flat surface during calibration.

        Args:
            samples: Number of samples to average
            delay_ms: Delay between samples in milliseconds

        Returns:
            ServiceResult
        """
        payload = ImuCalibratePayload(samples=samples, delay_ms=delay_ms)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            return ServiceResult.success(
                data=ImuCalibrateResponse(samples=samples, delay_ms=delay_ms)
            )
        else:
            return ServiceResult.failure(error=error or "Failed to calibrate IMU")

    async def set_bias(
        self,
        ax: float = 0.0,
        ay: float = 0.0,
        az: float = 0.0,
        gx: float = 0.0,
        gy: float = 0.0,
        gz: float = 0.0,
    ) -> ServiceResult:
        """
        Set IMU bias correction values manually.

        Args:
            ax: Accelerometer X bias
            ay: Accelerometer Y bias
            az: Accelerometer Z bias
            gx: Gyroscope X bias
            gy: Gyroscope Y bias
            gz: Gyroscope Z bias

        Returns:
            ServiceResult
        """
        accel_bias = [ax, ay, az]
        gyro_bias = [gx, gy, gz]
        payload = ImuSetBiasPayload(accel_bias=accel_bias, gyro_bias=gyro_bias)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            self._bias = ImuBias(ax=ax, ay=ay, az=az, gx=gx, gy=gy, gz=gz)
            return ServiceResult.success(
                data=ImuSetBiasResponse(
                    accel_bias=(ax, ay, az),
                    gyro_bias=(gx, gy, gz),
                )
            )
        else:
            return ServiceResult.failure(error=error or "Failed to set IMU bias")

    async def zero(self) -> ServiceResult:
        """
        Zero current orientation as reference.

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable("CMD_IMU_ZERO", {})

        if ok:
            return ServiceResult.success()
        else:
            return ServiceResult.failure(error=error or "Failed to zero IMU")

    def update_reading(self, reading: ImuReading) -> None:
        """
        Update last reading (called from telemetry handler).

        Args:
            reading: New IMU reading
        """
        self._last_reading = reading
