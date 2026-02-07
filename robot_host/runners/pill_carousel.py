from __future__ import annotations
import asyncio
import time
from typing import Optional

from robot_host.core.event_bus import EventBus
from robot_host.command.client import AsyncRobotClient
from robot_host.module.pill_test import PillCarousel, PillCarouselConfig
from robot_host.transport.tcp_transport import AsyncTcpTransport
from robot_host.transport.serial_transport import SerialTransport


# ==================== SIMPLE CONFIG BLOCK ====================

# Choose "serial" or "tcp"
TRANSPORT_TYPE = "serial"

# Serial settings
SERIAL_PORT = "/dev/cu.usbserial-0001"
SERIAL_BAUD = 115200

# TCP settings (AP mode)
TCP_STA = "10.0.0.60"
TCP_HOST = "192.168.4.1"
TCP_PORT = 3333

# Carousel / motion config
MOTOR_ID = 0
STEPS_PER_REV = 200       # same 'steps_per_rev' you use now
SLOTS_PER_REV = 5
SPEED_RPS = 0.5           # revolutions per second
COVER_OFFSET_STEPS = 17   # NEW: 20-step nudge to cover a slot

# What test to run
FULL_REV_TEST = False    # True = one full rev, False = step slot-by-slot
COVER_DEMO = True       # NEW: if True, cover/uncover each slot after moving


async def tcp_preflight(host: str, port: int, timeout: float = 1.0) -> bool:
    """
    One-shot TCP check to avoid hanging when ESP isn't reachable.
    Copied from your stepper runner.
    """
    print(f"[PillCarouselTest] Preflight TCP check to {host}:{port} ...")
    try:
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
    except Exception as e:
        print(f"[PillCarouselTest] Preflight FAILED: {e!r}")
        return False
    else:
        print("[PillCarouselTest] Preflight SUCCESS")
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True


# ==================== MAIN LOGIC ====================

async def run_pill_carousel():
    bus = EventBus()

    # --- Pick transport based on constant ---
    if TRANSPORT_TYPE == "tcp":
        ok = await tcp_preflight(TCP_STA, TCP_PORT, timeout=1.0)
        if not ok:
            print("[PillCarouselTest] Aborting: TCP endpoint not reachable.")
            return

        print(f"[PillCarouselTest] Using TCP transport to {TCP_HOST}:{TCP_PORT}")
        transport = AsyncTcpTransport(host=TCP_HOST, port=TCP_PORT)

    elif TRANSPORT_TYPE == "serial":
        print(f"[PillCarouselTest] Using SERIAL transport on {SERIAL_PORT} @ {SERIAL_BAUD}")
        transport = SerialTransport(port=SERIAL_PORT, baudrate=SERIAL_BAUD)

    else:
        raise ValueError(f"Unknown TRANSPORT_TYPE: {TRANSPORT_TYPE}")

    client = AsyncRobotClient(transport=transport, bus=bus)

    # --- Connect ---
    try:
        print("[PillCarouselTest] Connecting client...")
        await client.start()
    except Exception as e:
        print(f"[PillCarouselTest] FAILED to start client: {e!r}")
        return

    print("[PillCarouselTest] Client started")

    # Build carousel controller
    config = PillCarouselConfig(
        motor_id=MOTOR_ID,
        steps_per_rev=STEPS_PER_REV,
        slots_per_rev=SLOTS_PER_REV,
        default_speed_rps=SPEED_RPS,
        cover_offset_steps=COVER_OFFSET_STEPS,
    )
    carousel = PillCarousel(client, config)

    try:
        # Init robot (telem, estop, modes, enable stepper)
        await carousel.init_robot(telem_interval_ms=500)

        # Manually align the carousel so current physical slot = 0,
        # then we tell the controller that.
        carousel.set_current_slot(0)

        if FULL_REV_TEST:
            print("=== Full revolution test ===")
            await carousel.spin_full_rev()
        else:
            print("=== Slot-by-slot test ===")
            for i in range(SLOTS_PER_REV):
                await asyncio.sleep(0.5)
                await carousel.step_to_next_slot()

                if COVER_DEMO:
                    # show the 20-step cover + 20-step uncover motion per slot
                    await asyncio.sleep(0.5)
                    await carousel.cover_current_slot()
                    await asyncio.sleep(0.5)
                    await carousel.uncover_current_slot()

        print("[PillCarouselTest] Done stepping slots")
    finally:
        print("[PillCarouselTest] Shutting down robot...")
        await carousel.shutdown_robot()
        print("[PillCarouselTest] Stopping client...")
        await client.stop()
        print("[PillCarouselTest] Client stopped")


def main():
    print("[PillCarouselTest] Starting...")
    t0 = time.time()
    asyncio.run(run_pill_carousel())
    print(f"[PillCarouselTest] Done in {time.time() - t0:.2f}s")


if __name__ == "__main__":
    main()
