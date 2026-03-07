import asyncio
from typing import Any, Dict

from robot_host.core.event_bus import EventBus
from robot_host.command.client import AsyncRobotClient
from robot_host.transport.tcp_transport import AsyncTcpTransport
from robot_host.transport.serial_transport import SerialTransport  # or serial_transport
from robot_host.transport.bluetooth_transport import BluetoothSerialTransport

from robot_host.telemetry.host_module import TelemetryHostModule
from robot_host.telemetry.models import (
    ImuTelemetry,
    UltrasonicTelemetry,
    LidarTelemetry,
    StepperTelemetry,
    DcMotorTelemetry,
)


def attach_telemetry_prints(bus: EventBus) -> None:
    # ---------- helpers ----------

    def _get(obj: Any, attr: str, default=None):
        """
        Safely get attr whether obj is a dataclass or dict.
        """
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    # ---------- IMU ----------

    def on_imu(imu: Any) -> None:
        online = bool(_get(imu, "online", False))
        ok = _get(imu, "ok", None)

        ax = _get(imu, "ax_g", 0.0) or 0.0
        ay = _get(imu, "ay_g", 0.0) or 0.0
        az = _get(imu, "az_g", 0.0) or 0.0
        temp = _get(imu, "temp_c", 0.0) or 0.0

        print(
            f"[IMU] online={online} ok={ok} "
            f"ax={ax:+.3f}g ay={ay:+.3f}g az={az:+.3f}g "
            f"T={temp:.2f}°C"
        )

    # ---------- Ultrasonic ----------

    def on_ultra(ultra: Any) -> None:
        ts_ms = _get(ultra, "ts_ms", None)
        ts = f"{ts_ms}ms" if ts_ms is not None else "?"

        sensor_id = _get(ultra, "sensor_id", 0)
        attached = bool(_get(ultra, "attached", False))
        ok = _get(ultra, "ok", None)
        dist_val = _get(ultra, "distance_cm", None)
        dist = f"{dist_val:.1f} cm" if dist_val is not None else "N/A"

        print(
            f"[ULTRA] t={ts} id={sensor_id} "
            f"attached={attached} ok={ok} d={dist}"
        )

    # ---------- LiDAR ----------

    def on_lidar(lidar: Any) -> None:
        ts_ms = _get(lidar, "ts_ms", None)
        ts = f"{ts_ms}ms" if ts_ms is not None else "?"

        online = bool(_get(lidar, "online", False))
        ok = _get(lidar, "ok", None)
        d_val = _get(lidar, "distance_m", None)
        dist = f"{d_val:.3f} m" if d_val is not None else "N/A"
        sig_val = _get(lidar, "signal", None)
        sig = f"{sig_val:.1f}" if sig_val is not None else "N/A"

        print(
            f"[LIDAR] t={ts} online={online} ok={ok} "
            f"d={dist} signal={sig}"
        )

    # ---------- Stepper ----------

    def on_stepper(step: Any) -> None:
        ts_ms = _get(step, "ts_ms", None)
        ts = f"{ts_ms}ms" if ts_ms is not None else "?"

        motor_id = _get(step, "motor_id", "?")
        attached = bool(_get(step, "attached", False))
        enabled = bool(_get(step, "enabled", False))
        moving = bool(_get(step, "moving", False))
        dir_fwd = bool(_get(step, "dir_forward", True))
        last_steps = _get(step, "last_cmd_steps", 0)
        last_speed = _get(step, "last_cmd_speed", 0.0)

        print(
            f"[STEPPER] t={ts} motor={motor_id} attached={attached} "
            f"enabled={enabled} moving={moving} "
            f"dir_fwd={dir_fwd} "
            f"last_cmd_steps={last_steps} last_cmd_speed={last_speed}"
        )

    # ---------- DC motor ----------

    def on_dc(dc: Any) -> None:
        attached = bool(_get(dc, "attached", False))
        if not attached:
            print("[DC] motor0 not attached")
            return

        motor_id = _get(dc, "motor_id", 0)
        spd = _get(dc, "speed", 0.0) or 0.0
        freq = _get(dc, "freq_hz", 0.0) or 0.0
        res = _get(dc, "resolution_bits", 0) or 0

        print(
            f"[DC] id={motor_id} attached={attached} "
            f"speed={spd:+.3f} (norm) freq={freq:.0f} Hz res={res} bits"
        )

    # ---------- subscriptions ----------

    bus.subscribe("telemetry.imu", on_imu)
    bus.subscribe("telemetry.ultrasonic", on_ultra)
    bus.subscribe("telemetry.lidar", on_lidar)
    bus.subscribe("telemetry.stepper0", on_stepper)

    # Only subscribe to the real DC topic from TelemetryHostModule
    bus.subscribe("telemetry.dc_motor0", on_dc)


async def main() -> None:
    bus = EventBus()

    # Pick whatever transport you want here
    # transport = SerialTransport(port="/dev/cu.usbserial-0001", baudrate=115200)
    # transport = BluetoothSerialTransport.auto(device_name="ESP32-SPP", baudrate=115200)
    transport = AsyncTcpTransport(host="10.0.0.61", port=3333)

    client = AsyncRobotClient(transport, bus=bus)

    # Structured telemetry module
    telemetry = TelemetryHostModule(bus)  # noqa: F841 (keep it alive)

    # Attach pretty printers
    attach_telemetry_prints(bus)

    await client.start()

    on = False
    INTERVAL_ON_MS = 100    # ~10 Hz
    INTERVAL_OFF_MS = 1000  # slower / effectively off for you

    while True:
        on = not on
        interval = INTERVAL_ON_MS if on else INTERVAL_OFF_MS
        state = "ON" if on else "OFF"
        print(f"\n[TELEM] Setting telemetry {state} (interval_ms={interval})")
        await client.cmd_telem_set_interval(interval_ms=interval)
        await asyncio.sleep(5.0)


if __name__ == "__main__":
    asyncio.run(main())
