# mara_host/workflows/calibration/imu.py
"""
IMU calibration workflow.

Collects samples and calculates accelerometer/gyroscope offsets.
"""

import asyncio
from dataclasses import dataclass

from mara_host.workflows.base import BaseWorkflow, WorkflowResult, WorkflowState


@dataclass
class IMUSample:
    """Single IMU sample."""
    ax: float
    ay: float
    az: float
    gx: float
    gy: float
    gz: float


class IMUCalibrationWorkflow(BaseWorkflow):
    """
    IMU calibration workflow.

    Collects samples while the robot is stationary to calculate
    accelerometer and gyroscope bias offsets.

    Usage:
        workflow = IMUCalibrationWorkflow(client)
        workflow.on_progress = lambda p, s: print(f"{p}%: {s}")

        result = await workflow.run(num_samples=100)
        if result.ok:
            print(f"Accel offsets: {result.data['accel_offsets']}")
            print(f"Gyro offsets: {result.data['gyro_offsets']}")
    """

    def __init__(self, client):
        super().__init__(client)
        self._samples: list[IMUSample] = []
        self._collecting = False

    @property
    def name(self) -> str:
        return "IMU Calibration"

    async def run(
        self,
        num_samples: int = 100,
        sample_interval_ms: int = 50,
        gravity: float = 9.81,
    ) -> WorkflowResult:
        """
        Run IMU calibration.

        Args:
            num_samples: Number of samples to collect
            sample_interval_ms: Interval between samples in ms
            gravity: Expected gravity constant (m/s^2)

        Returns:
            WorkflowResult with accel_offsets and gyro_offsets in data
        """
        self.reset()
        self._set_state(WorkflowState.RUNNING)
        self._samples = []
        self._collecting = True

        try:
            self._emit_progress(0, "Place robot on flat, stable surface")
            await asyncio.sleep(2.0)  # Give user time to read

            self._emit_progress(5, "Collecting samples...")

            # Collect samples
            sample_interval = sample_interval_ms / 1000.0
            for i in range(num_samples):
                if self._check_cancelled():
                    return WorkflowResult.cancelled()

                progress = 5 + int((i / num_samples) * 85)
                self._emit_progress(progress, f"Sample {i+1}/{num_samples}")

                await asyncio.sleep(sample_interval)

            self._collecting = False

            # Calculate offsets
            if len(self._samples) < 10:
                return WorkflowResult.failure(
                    f"Insufficient samples: {len(self._samples)} (need at least 10)"
                )

            self._emit_progress(95, "Calculating offsets")

            # Average all samples
            n = len(self._samples)
            ax_avg = sum(s.ax for s in self._samples) / n
            ay_avg = sum(s.ay for s in self._samples) / n
            az_avg = sum(s.az for s in self._samples) / n
            gx_avg = sum(s.gx for s in self._samples) / n
            gy_avg = sum(s.gy for s in self._samples) / n
            gz_avg = sum(s.gz for s in self._samples) / n

            # Accel Z offset should account for gravity
            # Assuming Z is vertical, expected reading is +gravity
            az_offset = az_avg - gravity

            # Calculate variance for quality check
            ax_var = sum((s.ax - ax_avg) ** 2 for s in self._samples) / n
            ay_var = sum((s.ay - ay_avg) ** 2 for s in self._samples) / n
            az_var = sum((s.az - az_avg) ** 2 for s in self._samples) / n

            self._emit_progress(100, "Calibration complete")

            return WorkflowResult.success({
                "num_samples": n,
                "accel_offsets": [ax_avg, ay_avg, az_offset],
                "gyro_offsets": [gx_avg, gy_avg, gz_avg],
                "accel_variance": [ax_var, ay_var, az_var],
                "quality": "good" if max(ax_var, ay_var, az_var) < 0.1 else "poor",
            })

        except Exception as e:
            return WorkflowResult.failure(str(e))
        finally:
            self._collecting = False

    def add_sample(
        self,
        ax: float,
        ay: float,
        az: float,
        gx: float,
        gy: float,
        gz: float,
    ) -> None:
        """
        Add an IMU sample (called from telemetry).

        Args:
            ax, ay, az: Accelerometer readings (m/s^2)
            gx, gy, gz: Gyroscope readings (rad/s)
        """
        if self._collecting:
            self._samples.append(IMUSample(ax, ay, az, gx, gy, gz))
