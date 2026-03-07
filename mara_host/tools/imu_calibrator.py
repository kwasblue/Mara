# mara_host/tools/imu_calibrator.py

import asyncio
import numpy as np

class ImuCalibrator:
    def __init__(self, client, samples_needed=300):
        self.client = client
        self.samples_needed = samples_needed
        self._acc_samples = []
        self._gyro_samples = []
        self._done_event = asyncio.Event()

        # subscribe to processed IMU telemetry
        client.bus.subscribe("telemetry.imu", self._on_imu)

    def _on_imu(self, imu: dict) -> None:
        if not imu.get("ok", False):
            return
        if self._done_event.is_set():
            return

        acc = np.array([imu["ax_g"], imu["ay_g"], imu["az_g"]], dtype=float)
        gyro = np.array([imu["gx_dps"], imu["gy_dps"], imu["gz_dps"]], dtype=float)

        self._acc_samples.append(acc)
        self._gyro_samples.append(gyro)

        n = len(self._acc_samples)
        if n % 50 == 0:
            print(f"[IMU CAL] collected {n}/{self.samples_needed} samples...")

        if n >= self.samples_needed:
            self._done_event.set()

    async def run(self):
        print("[IMU CAL] Place the robot still and flat, then wait...")
        await self._done_event.wait()

        acc_arr = np.stack(self._acc_samples, axis=0)
        gyro_arr = np.stack(self._gyro_samples, axis=0)

        acc_mean = acc_arr.mean(axis=0)
        gyro_mean = gyro_arr.mean(axis=0)

        print(f"[IMU CAL] mean accel (g): {acc_mean}")
        print(f"[IMU CAL] mean gyro (dps): {gyro_mean}")

        # Assuming Z axis should read +1g at rest (board upright)
        gravity_vec = np.array([0.0, 0.0, 1.0])
        accel_bias = acc_mean - gravity_vec
        gyro_bias = gyro_mean  # stationary should be 0

        print(f"[IMU CAL] suggested accel_bias (g): {accel_bias}")
        print(f"[IMU CAL] suggested gyro_bias (dps):  {gyro_bias}")

        return accel_bias, gyro_bias
