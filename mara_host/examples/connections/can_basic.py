#!/usr/bin/env python3
# mara_host/runners/run_can_client.py
"""
CAN bus client example demonstrating hybrid native/protocol communication.

This runner shows how to:
    - Connect to a CAN bus interface
    - Send CAN-native velocity commands (real-time)
    - Receive encoder and IMU data (CAN-native)
    - Send JSON commands via protocol transport

Requirements:
    - python-can>=4.0.0
    - CAN interface configured (e.g., can0 on Linux, PCAN on macOS/Windows)

Linux setup (SocketCAN):
    sudo ip link set can0 type can bitrate 500000
    sudo ip link set can0 up

For testing without hardware, use virtual CAN:
    sudo modprobe vcan
    sudo ip link add dev vcan0 type vcan
    sudo ip link set vcan0 up
"""

import argparse
import asyncio
import logging
import time

from mara_host.command.client import MaraClient
from mara_host.transport.can_transport import CANTransport, VirtualCANTransport
from mara_host.transport.can_defs import NodeState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main(
    channel: str = "can0",
    bustype: str = "socketcan",
    node_id: int = 0,
    virtual: bool = False,
) -> None:
    """Run CAN client demo."""

    # Create transport
    if virtual:
        logger.info("Using virtual CAN bus (loopback mode)")
        transport = VirtualCANTransport(channel=channel, node_id=node_id)
    else:
        logger.info(f"Connecting to CAN bus: {channel} ({bustype})")
        transport = CANTransport(
            channel=channel,
            bustype=bustype,
            node_id=node_id,
        )

    # Set up native message callbacks
    transport.set_encoder_callback(
        lambda nid, counts, vel: logger.info(f"[Encoder] node={nid} counts={counts} vel={vel}")
    )
    transport.set_imu_accel_callback(
        lambda nid, ax, ay, az: logger.info(f"[IMU Accel] node={nid} ax={ax:.2f}g ay={ay:.2f}g az={az:.2f}g")
    )
    transport.set_imu_gyro_callback(
        lambda nid, gx, gy, gz: logger.info(f"[IMU Gyro] node={nid} gx={gx:.1f} gy={gy:.1f} gz={gz:.1f} dps")
    )
    transport.set_heartbeat_callback(
        lambda nid, uptime, state: logger.info(f"[Heartbeat] node={nid} uptime={uptime}ms state={state.name}")
    )
    transport.set_status_callback(
        lambda nid, status: logger.info(
            f"[Status] node={nid} state={NodeState(status.state).name} "
            f"armed={status.armed} active={status.active} "
            f"voltage={status.voltage_v:.2f}V temp={status.temp_c:.1f}C"
        )
    )

    # Create async client for protocol commands
    client = MaraClient(transport, connection_timeout_s=5.0)

    # Subscribe to protocol events
    client.bus.subscribe("heartbeat", lambda d: logger.info(f"[Protocol] HEARTBEAT {d}"))
    client.bus.subscribe("pong", lambda d: logger.info(f"[Protocol] PONG {d}"))
    client.bus.subscribe("json", lambda obj: logger.info(f"[Protocol] JSON: {obj}"))
    client.bus.subscribe("error", lambda err: logger.warning(f"[Protocol] ERROR: {err}"))

    await client.start()
    logger.info(f"CAN client started (node_id={node_id})")

    try:
        last_native_cmd = 0.0
        last_heartbeat = 0.0
        vx = 0.0
        omega = 0.0
        seq = 0

        while True:
            now = time.time()

            # Send heartbeat every 1 second
            if now - last_heartbeat >= 1.0:
                uptime_ms = int((now - transport.stats.start_time) * 1000)
                await transport.send_heartbeat(uptime_ms, NodeState.ACTIVE, load_pct=50)
                last_heartbeat = now

            # Send velocity command every 100ms (10 Hz) as demo
            if now - last_native_cmd >= 0.1:
                # Oscillate velocity for demo
                vx = 0.2 * (1.0 if int(now) % 4 < 2 else -1.0)
                omega = 0.1 * (1.0 if int(now) % 2 == 0 else -1.0)
                seq += 1

                await transport.send_velocity(vx, omega, seq)
                logger.debug(f"[TX] Velocity vx={vx:.2f} omega={omega:.2f} seq={seq}")
                last_native_cmd = now

            # Print stats periodically
            if seq % 100 == 0 and seq > 0:
                stats = transport.stats
                logger.info(
                    f"[Stats] TX={stats.tx_count} RX={stats.rx_count} "
                    f"native_tx={stats.native_tx_count} proto_tx={stats.proto_tx_count} "
                    f"errors={stats.tx_errors + stats.rx_errors}"
                )

            await asyncio.sleep(0.01)

    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        await client.stop()
        logger.info("CAN client stopped")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="CAN bus client demo")
    parser.add_argument(
        "-c", "--channel",
        default="can0",
        help="CAN interface name (default: can0)"
    )
    parser.add_argument(
        "-b", "--bustype",
        default="socketcan",
        help="CAN bus type (default: socketcan)"
    )
    parser.add_argument(
        "-n", "--node-id",
        type=int,
        default=0,
        help="Local node ID 0-14 (default: 0)"
    )
    parser.add_argument(
        "-v", "--virtual",
        action="store_true",
        help="Use virtual CAN bus (for testing without hardware)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(
        channel=args.channel,
        bustype=args.bustype,
        node_id=args.node_id,
        virtual=args.virtual,
    ))
