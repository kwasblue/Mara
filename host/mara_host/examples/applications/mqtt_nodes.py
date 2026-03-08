#!/usr/bin/env python3
"""
Example runner for MQTT multi-node communication.

This demonstrates how to:
1. Connect to MQTT broker
2. Discover nodes on the network
3. Control multiple nodes simultaneously

Usage:
    python -m mara_host.runners.run_mqtt_nodes --broker 192.168.1.100

    # With fallback broker (e.g., node0's built-in broker)
    python -m mara_host.runners.run_mqtt_nodes --broker 192.168.1.100 --fallback 192.168.1.1
"""

import argparse
import asyncio

from mara_host.core.event_bus import EventBus
from mara_host.transport.mqtt import NodeManager


async def main(
    broker_host: str,
    broker_port: int,
    fallback_broker: str | None,
    discover_timeout: float,
    require_handshake: bool = True,
) -> None:
    """Main entry point."""
    print(f"MQTT Multi-Node Example")
    print(f"Broker: {broker_host}:{broker_port}")
    if fallback_broker:
        print(f"Fallback: {fallback_broker}")
    if not require_handshake:
        print("Handshake: DISABLED (--no-handshake)")
    print()

    # Create event bus and node manager
    bus = EventBus()

    # Subscribe to events
    bus.subscribe("node.discovered", lambda d: print(f"[Event] Node discovered: {d['node_id']}"))
    bus.subscribe("node.added", lambda d: print(f"[Event] Node added: {d['node_id']}"))

    manager = NodeManager(
        bus=bus,
        broker_host=broker_host,
        broker_port=broker_port,
        fallback_broker=fallback_broker,
        require_version_match=require_handshake,
    )

    try:
        await manager.start()

        # Discover nodes
        print(f"Discovering nodes (timeout={discover_timeout}s)...")
        nodes = await manager.discover(timeout_s=discover_timeout)

        if not nodes:
            print("No nodes discovered.")
            return

        print(f"\nDiscovered {len(nodes)} node(s):")
        for info in nodes:
            print(f"  - {info.node_id}: {info.board or 'unknown'} @ {info.ip or '?'}")
            print(f"    Firmware: {info.firmware}, Protocol: {info.protocol}")

        # Get first node
        node0 = manager.get_node(nodes[0].node_id)
        if node0:
            print(f"\nConnecting to {node0.node_id}...")

            # Wait for handshake
            await asyncio.sleep(2.0)

            if node0.is_online:
                print(f"Node {node0.node_id} is online!")
                print(f"  Firmware: {node0.client.firmware_version}")
                print(f"  Protocol: {node0.client.protocol_version}")

                # Example: send a command
                print("\nSending CMD_STOP to all nodes...")
                results = await manager.broadcast_stop()
                for node_id, (success, error) in results.items():
                    status = "OK" if success else f"FAILED: {error}"
                    print(f"  {node_id}: {status}")
            else:
                print(f"Node {node0.node_id} is not online (handshake may have failed)")

        # Keep running
        print("\nPress Ctrl+C to exit...")
        while True:
            await asyncio.sleep(1.0)

            # Print online status
            online = manager.get_online_nodes()
            offline = manager.get_offline_nodes()
            if offline:
                print(f"Online: {online}, Offline: {offline}")

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await manager.stop()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MQTT Multi-Node Example",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--broker", "-b",
        type=str,
        default="localhost",
        help="MQTT broker hostname or IP",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=1883,
        help="MQTT broker port",
    )
    parser.add_argument(
        "--fallback", "-f",
        type=str,
        default=None,
        help="Fallback MQTT broker (e.g., node0's built-in broker)",
    )
    parser.add_argument(
        "--discover-timeout", "-t",
        type=float,
        default=5.0,
        help="Discovery timeout in seconds",
    )
    parser.add_argument(
        "--no-handshake",
        action="store_true",
        help="Skip version handshake (for testing firmware without full protocol)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(
        broker_host=args.broker,
        broker_port=args.port,
        fallback_broker=args.fallback,
        discover_timeout=args.discover_timeout,
        require_handshake=not args.no_handshake,
    ))
