# robot_host/telemetry/file_logger.py
from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Any

from robot_host.core.event_bus import EventBus
from .models import ImuTelemetry, UltrasonicTelemetry


class TelemetryFileLogger:
    def __init__(self, bus: EventBus, log_dir: Path) -> None:
        self._log_dir = log_dir

        self._imu_fp = None
        self._ultra_fp = None

        self._imu_writer: Optional[csv.writer] = None
        self._ultra_writer: Optional[csv.writer] = None

        # Topics published by TelemetryHostModule
        bus.subscribe("telemetry.imu", self._on_imu)
        bus.subscribe("telemetry.ultrasonic", self._on_ultra)

    def start(self) -> None:
        self._log_dir.mkdir(parents=True, exist_ok=True)

        imu_path = self._log_dir / "imu.csv"
        ultra_path = self._log_dir / "ultrasonic.csv"

        self._imu_fp = imu_path.open("w", newline="")
        self._ultra_fp = ultra_path.open("w", newline="")

        self._imu_writer = csv.writer(self._imu_fp)
        self._ultra_writer = csv.writer(self._ultra_fp)

        # Include timestamp if available
        self._imu_writer.writerow(
            [
                "ts_ms",
                "ax_g",
                "ay_g",
                "az_g",
                "gx_dps",
                "gy_dps",
                "gz_dps",
                "temp_c",
                "ok",
                "online",
            ]
        )

        self._ultra_writer.writerow(
            [
                "ts_ms",
                "sensor_id",
                "attached",
                "ok",
                "distance_cm",
            ]
        )

    def stop(self) -> None:
        if self._imu_fp:
            self._imu_fp.close()
            self._imu_fp = None
        if self._ultra_fp:
            self._ultra_fp.close()
            self._ultra_fp = None

        self._imu_writer = None
        self._ultra_writer = None

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #

    def _on_imu(self, imu: Any) -> None:
        """
        Handle IMU telemetry.

        Accepts either:
          - ImuTelemetry model
          - dict with corresponding keys (fallback)
        """
        if not self._imu_writer:
            return

        # Normalize to dict-like access
        if isinstance(imu, ImuTelemetry):
            # Direct attribute access (ts_ms may not exist on model, use None)
            ts_ms = imu.ts_ms if hasattr(imu, "ts_ms") else None
            row = [
                ts_ms,
                imu.ax_g,
                imu.ay_g,
                imu.az_g,
                imu.gx_dps,
                imu.gy_dps,
                imu.gz_dps,
                imu.temp_c,
                imu.ok,
                imu.online,
            ]
        elif isinstance(imu, dict):
            # Fallback if something still publishes a raw dict
            ts_ms = imu.get("ts_ms")
            row = [
                ts_ms,
                imu.get("ax_g"),
                imu.get("ay_g"),
                imu.get("az_g"),
                imu.get("gx_dps"),
                imu.get("gy_dps"),
                imu.get("gz_dps"),
                imu.get("temp_c"),
                imu.get("ok"),
                imu.get("online"),
            ]
        else:
            # Unknown type, ignore silently
            return

        self._imu_writer.writerow(row)

    def _on_ultra(self, ultra: Any) -> None:
        """
        Handle Ultrasonic telemetry.

        Accepts either:
          - UltrasonicTelemetry model
          - dict with corresponding keys (fallback)
        """
        if not self._ultra_writer:
            return

        if isinstance(ultra, UltrasonicTelemetry):
            ts_ms = ultra.ts_ms if hasattr(ultra, "ts_ms") else None
            row = [
                ts_ms,
                ultra.sensor_id,
                ultra.attached,
                ultra.ok,
                ultra.distance_cm,
            ]
        elif isinstance(ultra, dict):
            ts_ms = ultra.get("ts_ms")
            row = [
                ts_ms,
                ultra.get("sensor_id"),
                ultra.get("attached"),
                ultra.get("ok"),
                ultra.get("distance_cm"),
            ]
        else:
            return

        self._ultra_writer.writerow(row)
