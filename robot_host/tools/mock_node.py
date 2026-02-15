#!/usr/bin/env python3
"""
Mock ESP32 node for multi-node testing.

Simulates an ESP32 control node over MQTT without needing real hardware.

Usage:
    python -m robot_host.tools.mock_node --node-id node1 --broker 10.0.0.59
    python -m robot_host.tools.mock_node --node-id node2 --broker 10.0.0.59
"""

import argparse
import asyncio
import json

import aiomqtt

from robot_host.core import protocol


class MockNode:
    """Simulates an ESP32 node over MQTT."""

    def __init__(
        self,
        node_id: str,
        broker_host: str,
        broker_port: int = 1883,
        firmware: str = "1.0.0-mock",
        board: str = "mock-esp32",
    ) -> None:
        self.node_id = node_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.firmware = firmware
        self.board = board

        # Topics
        self.topic_cmd = f"mara/{node_id}/cmd"
        self.topic_ack = f"mara/{node_id}/ack"
        self.topic_telemetry = f"mara/{node_id}/telemetry"
        self.topic_discover = "mara/fleet/discover"
        self.topic_discover_response = "mara/fleet/discover_response"

        self._running = False
        self._client: aiomqtt.Client | None = None

    async def run(self) -> None:
        """Run the mock node."""
        self._running = True
        print(f"[MockNode:{self.node_id}] Starting...")
        print(f"[MockNode:{self.node_id}] Broker: {self.broker_host}:{self.broker_port}")

        while self._running:
            try:
                async with aiomqtt.Client(
                    hostname=self.broker_host,
                    port=self.broker_port,
                    identifier=f"mock-{self.node_id}",
                ) as client:
                    self._client = client
                    print(f"[MockNode:{self.node_id}] Connected!")

                    # Subscribe to topics
                    await client.subscribe(self.topic_cmd)
                    await client.subscribe(self.topic_discover)
                    print(f"[MockNode:{self.node_id}] Subscribed to {self.topic_cmd}, {self.topic_discover}")

                    # Announce ourselves
                    await self._publish_discovery_response()

                    # Process messages
                    async for message in client.messages:
                        if not self._running:
                            break
                        await self._handle_message(message)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[MockNode:{self.node_id}] Error: {e}")
                if self._running:
                    await asyncio.sleep(2.0)

        print(f"[MockNode:{self.node_id}] Stopped")

    def stop(self) -> None:
        """Stop the mock node."""
        self._running = False

    async def _handle_message(self, message: aiomqtt.Message) -> None:
        """Handle incoming MQTT message."""
        topic = str(message.topic)

        if topic == self.topic_discover:
            # Discovery request - respond with our info
            await self._publish_discovery_response()
            return

        if topic == self.topic_cmd:
            # Command received - parse and respond
            payload = message.payload
            if isinstance(payload, (bytes, bytearray)):
                await self._handle_command(bytes(payload))
            return

    async def _handle_command(self, raw: bytes) -> None:
        """Handle a command frame."""
        # Parse frame using protocol
        frames = []
        buffer = bytearray(raw)
        protocol.extract_frames(buffer, lambda body: frames.append(bytes(body)))

        for body in frames:
            if len(body) < 1:
                continue

            msg_type = body[0]
            payload = body[1:] if len(body) > 1 else b""

            print(f"[MockNode:{self.node_id}] RX msg_type=0x{msg_type:02X}, len={len(payload)}")

            # Handle specific message types
            if msg_type == protocol.MSG_VERSION_REQUEST:
                await self._send_version_response()
            elif msg_type == protocol.MSG_PING:
                await self._send_pong()
            elif msg_type == protocol.MSG_CMD_JSON:
                await self._handle_json_command(payload)
            elif msg_type == protocol.MSG_CMD_BIN:
                await self._handle_bin_command(payload)
            else:
                print(f"[MockNode:{self.node_id}] Unknown msg_type=0x{msg_type:02X}")

    async def _send_version_response(self) -> None:
        """Send VERSION_RESPONSE."""
        response = {
            "firmware": self.firmware,
            "protocol": 1,
            "schema_version": 0,
            "board": self.board,
            "name": self.node_id,
            "features": [],
            "kind": "identity",
        }
        json_bytes = json.dumps(response).encode("utf-8")
        frame = protocol.encode(protocol.MSG_VERSION_RESPONSE, json_bytes)
        await self._publish_ack(frame)
        print(f"[MockNode:{self.node_id}] TX VERSION_RESPONSE")

    async def _send_pong(self) -> None:
        """Send PONG response."""
        frame = protocol.encode(protocol.MSG_PONG, b"")
        await self._publish_ack(frame)
        print(f"[MockNode:{self.node_id}] TX PONG")

    async def _handle_json_command(self, payload: bytes) -> None:
        """Handle JSON command."""
        try:
            cmd = json.loads(payload.decode("utf-8"))
            cmd_type = cmd.get("type", cmd.get("cmd", "unknown"))
            seq = cmd.get("seq", 0)
            print(f"[MockNode:{self.node_id}] JSON cmd: {cmd_type} seq={seq}")

            # Simulate success for all commands
            await self._send_json_ack(cmd_type, seq, True)

        except json.JSONDecodeError as e:
            print(f"[MockNode:{self.node_id}] JSON decode error: {e}")
            await self._send_json_ack("error", 0, False, str(e))

    async def _handle_bin_command(self, payload: bytes) -> None:
        """Handle binary command."""
        if len(payload) < 1:
            return

        opcode = payload[0]
        print(f"[MockNode:{self.node_id}] BIN cmd: opcode=0x{opcode:02X}")

        # Simulate success (binary commands don't have seq, use 0)
        await self._send_json_ack(f"bin_0x{opcode:02X}", 0, True)

    async def _send_json_ack(self, cmd: str, seq: int, success: bool, error: str | None = None) -> None:
        """Send JSON ACK response matching host's expected format."""
        response = {
            "type": "ACK",
            "cmd": cmd,
            "seq": seq,
            "src": "mcu",
            "ok": success,
        }
        if error:
            response["error"] = error

        json_bytes = json.dumps(response).encode("utf-8")
        frame = protocol.encode(protocol.MSG_CMD_JSON, json_bytes)
        await self._publish_ack(frame)
        print(f"[MockNode:{self.node_id}] TX ACK cmd={cmd} seq={seq} ok={success}")

    async def _publish_ack(self, data: bytes) -> None:
        """Publish to ack topic."""
        if self._client:
            await self._client.publish(self.topic_ack, data)

    async def _publish_discovery_response(self) -> None:
        """Publish discovery response."""
        response = {
            "node_id": self.node_id,
            "robot_id": self.node_id,
            "firmware": self.firmware,
            "protocol": 1,
            "board": self.board,
            "state": "online",
            "features": [],
        }
        if self._client:
            await self._client.publish(
                self.topic_discover_response,
                json.dumps(response).encode("utf-8"),
            )
            print(f"[MockNode:{self.node_id}] Published discovery response")


async def main(args: argparse.Namespace) -> None:
    """Main entry point."""
    node = MockNode(
        node_id=args.node_id,
        broker_host=args.broker,
        broker_port=args.port,
        firmware=args.firmware,
        board=args.board,
    )

    try:
        await node.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        node.stop()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Mock ESP32 node for multi-node testing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--node-id", "-n",
        type=str,
        default="node1",
        help="Node ID (e.g., node1, node2)",
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
        "--firmware", "-f",
        type=str,
        default="1.0.0-mock",
        help="Firmware version to report",
    )
    parser.add_argument(
        "--board",
        type=str,
        default="mock-esp32",
        help="Board type to report",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))
