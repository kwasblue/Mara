# mara_host/services/control/imu_service.py
"""
IMU sensor service.

Provides high-level control for IMU (accelerometer/gyroscope) sensors.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class ImuReading:
    """IMU sensor reading."""

    # Accelerometer (m/s^2)
    ax: float = 0.0
    ay: float = 0.0
    az: float = 0.0

    # Gyroscope (rad/s)
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

    async def read(self) -> ServiceResult:
        """
        Request IMU reading from MCU.

        Note: The actual values come via telemetry.

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable("CMD_IMU_READ", {})

        if ok:
            return ServiceResult.success()
        else:
            return ServiceResult.failure(error=error or "Failed to read IMU")

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
        ok, error = await self.client.send_reliable(
            "CMD_IMU_CALIBRATE",
            {
                "samples": samples,
                "delay_ms": delay_ms,
            },
        )

        if ok:
            return ServiceResult.success(
                data={"samples": samples, "delay_ms": delay_ms}
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
        ok, error = await self.client.send_reliable(
            "CMD_IMU_SET_BIAS",
            {
                "accel_bias": [ax, ay, az],
                "gyro_bias": [gx, gy, gz],
            },
        )

        if ok:
            self._bias = ImuBias(ax=ax, ay=ay, az=az, gx=gx, gy=gy, gz=gz)
            return ServiceResult.success(
                data={"accel_bias": [ax, ay, az], "gyro_bias": [gx, gy, gz]}
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
