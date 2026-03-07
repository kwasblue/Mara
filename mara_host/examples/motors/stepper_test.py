from __future__ import annotations
from typing import Optional

import asyncio
import argparse

from mara_host.core.event_bus import EventBus
from mara_host.command.client import MaraClient
from mara_host.transport.tcp_transport import AsyncTcpTransport
from mara_host.transport.serial_transport import SerialTransport


# === Defaults ===

DEFAULT_SERIAL_PORT = "/dev/cu.usbserial-0001"  # update to your actual device
DEFAULT_BAUD = 115200

# For TCP: AP first, STA optional
DEFAULT_AP_HOST = "192.168.4.1"
DEFAULT_STA_HOST = "10.0.0.60"   # keep around for later if you want
DEFAULT_TCP_HOST = DEFAULT_STA_HOST
DEFAULT_TCP_PORT = 3333


async def tcp_preflight(host: str, port: int, timeout: float = 1.0) -> bool:
    """
    Try a one-shot TCP connection to verify the host:port is reachable.
    If this fails, we do NOT construct MaraClient / AsyncTcpTransport.
    """
    print(f"[StepperRunner] Preflight TCP check to {host}:{port} ...")
    try:
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
    except Exception as e:
        print(f"[StepperRunner] Preflight FAILED: {e!r}")
        return False
    else:
        print("[StepperRunner] Preflight SUCCESS, endpoint reachable")
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True


async def run_stepper(
    transport_type: str,
    tcp_host: str,
    tcp_port: int,
    serial_port: str,
    baudrate: int,
    motor_id: int,
    steps: int,
    speed_rps: float,
    steps_per_rev: int,
    repeats: int,
    dwell: float,
):
    bus = EventBus()

    # --- Transport selection ---
    if transport_type == "tcp":
        # PRECHECK: don't even start the client if the network is unreachable
        ok = await tcp_preflight(tcp_host, tcp_port, timeout=1.0)
        if not ok:
            print("[StepperRunner] Aborting: TCP endpoint not reachable, no commands sent.")
            return

        print(f"[StepperRunner] Using TCP transport to {tcp_host}:{tcp_port}")
        transport = AsyncTcpTransport(host=tcp_host, port=tcp_port)

    elif transport_type == "serial":
        print(f"[StepperRunner] Using SERIAL transport on {serial_port} @ {baudrate}")
        transport = SerialTransport(port=serial_port, baudrate=baudrate)

    else:
        raise ValueError(f"Unknown transport type: {transport_type}")

    client = MaraClient(transport=transport, bus=bus)

    # --- Connect FIRST, no commands before this succeeds ---
    try:
        print("[StepperRunner] Connecting client...")
        await client.start()
    except Exception as e:
        print(f"[StepperRunner] FAILED to start client: {e!r}")
        return

    print("[StepperRunner] Client started, ready to send stepper commands")

    try:
        # Small settle delay to let MCU/router finish setup
        await asyncio.sleep(0.1)

        # Optional: slow telemetry
        try:
            await client.send_json_cmd("CMD_TELEM_SET_INTERVAL", {"interval_ms": 500})
        except Exception:
            pass

        # --- Safety + mode, DC-style ---
        print("[StepperRunner] Clearing ESTOP")
        await client.send_json_cmd("CMD_CLEAR_ESTOP", {})

        print("[StepperRunner] Setting mode=ARMED")
        await client.send_json_cmd("CMD_SET_MODE", {"mode": "ARMED"})

        print("[StepperRunner] Setting mode=ACTIVE")
        await client.send_json_cmd("CMD_SET_MODE", {"mode": "ACTIVE"})

        # --- Enable stepper driver ---
        print(f"[StepperRunner] Enabling stepper motor_id={motor_id}")
        await client.send_json_cmd(
            "CMD_STEPPER_ENABLE",
            {"motor_id": motor_id, "enable": True},
        )

        # Convert rev/s to steps/s, like you had
        speed_steps_s = speed_rps * steps_per_rev
        print(
            f"[StepperRunner] Using speed_steps_s={speed_steps_s} "
            f"(from {speed_rps} rps, {steps_per_rev} steps/rev)"
        )

        # --- Back-and-forth stepping ---
        for i in range(1, repeats + 1):
            print(f"[StepperRunner] Cycle {i}/{repeats}")

            print(f"[StepperRunner]  -> FWD {steps} steps")
            await client.send_json_cmd(
                "CMD_STEPPER_MOVE_REL",
                {
                    "motor_id": motor_id,
                    "steps": steps,
                    "speed_steps_s": speed_steps_s,
                },
            )
            await asyncio.sleep(dwell)

            print(f"[StepperRunner]  -> REV {steps} steps")
            await client.send_json_cmd(
                "CMD_STEPPER_MOVE_REL",
                {
                    "motor_id": motor_id,
                    "steps": -steps,
                    "speed_steps_s": speed_steps_s,
                },
            )
            await asyncio.sleep(dwell)

        # --- Stop + disable ---
        print("[StepperRunner] Stopping stepper")
        await client.send_json_cmd("CMD_STEPPER_STOP", {"motor_id": motor_id})

        print("[StepperRunner] Disabling stepper")
        await client.send_json_cmd(
            "CMD_STEPPER_ENABLE",
            {"motor_id": motor_id, "enable": False},
        )

        print("[StepperRunner] Done stepping")
    finally:
        print("[StepperRunner] Client stopping...")
        await client.stop()
        print("[StepperRunner] Client stopped")


def main():
    parser = argparse.ArgumentParser(
        description="Stepper runner for Python host (TCP or Serial), DC-ping style"
    )

    parser.add_argument(
        "--transport",
        choices=["tcp", "serial"],
        default="serial",   # <<< DEFAULT TO SERIAL NOW
        help="Which transport to use to reach the MCU",
    )

    # TCP options — default to AP IP
    parser.add_argument(
        "--tcp-host",
        default=DEFAULT_TCP_HOST,
        help="ESP32 TCP host/IP (default AP 192.168.4.1)",
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=DEFAULT_TCP_PORT,
        help="ESP32 TCP port",
    )

    # Serial options
    parser.add_argument(
        "--serial-port",
        default=DEFAULT_SERIAL_PORT,
        help="Serial device for ESP32 (e.g. /dev/cu.usbserial-0001, COM3)",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=DEFAULT_BAUD,
        help="Serial baudrate",
    )

    # Motion params
    parser.add_argument("--motor-id", type=int, default=0, help="Logical stepper motor_id")
    parser.add_argument("--steps", type=int, default=200, help="Relative steps per move")
    parser.add_argument(
        "--speed-rps",
        type=float,
        default=1.0,
        help="Speed in revolutions per second (converted to steps/s)",
    )
    parser.add_argument(
        "--steps-per-rev",
        type=int,
        default=200,
        help="Stepper steps per revolution (before microstepping)",
    )
    parser.add_argument("--repeats", type=int, default=5, help="Back-and-forth cycles")
    parser.add_argument("--dwell", type=float, default=0.5, help="Pause between moves (seconds)")

    args = parser.parse_args()

    asyncio.run(
        run_stepper(
            transport_type=args.transport,
            tcp_host=args.tcp_host,
            tcp_port=args.tcp_port,
            serial_port=args.serial_port,
            baudrate=args.baud,
            motor_id=args.motor_id,
            steps=args.steps,
            speed_rps=args.speed_rps,
            steps_per_rev=args.steps_per_rev,
            repeats=args.repeats,
            dwell=args.dwell,
        )
    )


if __name__ == "__main__":
    main()
