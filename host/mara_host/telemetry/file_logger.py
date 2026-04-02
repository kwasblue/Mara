# mara_host/telemetry/file_logger.py
from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Any

from mara_host.core.event_bus import EventBus
from .models import ImuTelemetry, UltrasonicTelemetry


class TelemetryFileLogger:
    """
    File logger for telemetry data.

    Lifecycle:
    - __init__: Store references, do NOT start logging
    - start(): Open files, subscribe to events, begin logging
    - stop(): Unsubscribe from events, close files

    Events arriving before start() or after stop() are ignored.
    """

    def __init__(self, bus: EventBus, log_dir: Path) -> None:
        self._bus = bus
        self._log_dir = log_dir

        self._imu_fp = None
        self._ultra_fp = None

        self._imu_writer: Optional[csv.writer] = None
        self._ultra_writer: Optional[csv.writer] = None

        # Track subscriptions for cleanup
        self._subscribed = False

    def start(self) -> None:
        """Start logging - open files and subscribe to events."""
        # Subscribe to events AFTER opening files to avoid race
        # where events arrive before we're ready to write
        self._log_dir.mkdir(parents=True, exist_ok=True)

        imu_path = self._log_dir / "imu.csv"
        ultra_path = self._log_dir / "ultrasonic.csv"

        # Open files with cleanup on partial failure
        try:
            self._imu_fp = imu_path.open("w", newline="")
            self._ultra_fp = ultra_path.open("w", newline="")
        except Exception:
            # Clean up any opened files on failure
            if self._imu_fp:
                self._imu_fp.close()
                self._imu_fp = None
            raise

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

        # Subscribe to events AFTER files are ready
        if not self._subscribed:
            self._bus.subscribe("telemetry.imu", self._on_imu)
            self._bus.subscribe("telemetry.ultrasonic", self._on_ultra)
            self._subscribed = True

    def stop(self) -> None:
        """Unsubscribe from events and close file handles safely."""
        # Unsubscribe first to prevent new events during cleanup
        if self._subscribed:
            try:
                self._bus.unsubscribe("telemetry.imu", self._on_imu)
                self._bus.unsubscribe("telemetry.ultrasonic", self._on_ultra)
            except Exception:
                pass  # Best-effort cleanup
            self._subscribed = False

        # Close all file handles, suppressing errors to ensure all get closed
        for fp_name in ('_imu_fp', '_ultra_fp'):
            fp = getattr(self, fp_name, None)
            if fp:
                try:
                    fp.close()
                except Exception:
                    pass  # Best-effort cleanup
                setattr(self, fp_name, None)

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
