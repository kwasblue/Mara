import asyncio
import json
import threading
from typing import Any

from mara_host.config.version import PROTOCOL_VERSION
from mara_host.core import protocol


class FakeMaraTcpServer:
    """Tiny TCP fake for host/runtime tests.

    Supports:
    - version/identity handshake
    - JSON command ACKs with optional command-specific payload overrides
    - thread-backed mode for sync HTTP/TestClient end-to-end tests
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.server = None
        self._connections = []
        self._tasks = set()
        self.command_log: list[dict[str, Any]] = []
        self.ack_overrides: dict[str, dict[str, Any]] = {}
        self.identity = {
            "protocol": PROTOCOL_VERSION,
            "firmware": "fake-fw",
            "schema_version": 1,
            "capabilities": 0,
            "features": ["gpio", "encoder", "imu", "servo"],
            "board": "fake-esp32",
            "name": "fake-mara",
        }
        self._thread = None
        self._thread_loop = None
        self._thread_ready = None

    async def start(self):
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        sock = self.server.sockets[0]
        self.port = sock.getsockname()[1]
        return self

    async def stop(self):
        for task in list(self._tasks):
            task.cancel()
        for writer in list(self._connections):
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        self._connections.clear()
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    def start_in_thread(self):
        if self._thread is not None:
            return self

        ready = threading.Event()
        self._thread_ready = ready

        def _runner():
            loop = asyncio.new_event_loop()
            self._thread_loop = loop
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start())
            ready.set()
            try:
                loop.run_forever()
            finally:
                loop.run_until_complete(self.stop())
                loop.close()

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()
        ready.wait(timeout=5)
        if not ready.is_set():
            raise RuntimeError("FakeMaraTcpServer failed to start in thread")
        return self

    def stop_threaded(self):
        if self._thread_loop is None or self._thread is None:
            return
        self._thread_loop.call_soon_threadsafe(self._thread_loop.stop)
        self._thread.join(timeout=5)
        self._thread = None
        self._thread_loop = None
        self._thread_ready = None

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._connections.append(writer)
        buffer = bytearray()
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                buffer.extend(data)
                protocol.extract_frames(buffer, lambda body: self._on_frame(body, writer))
        finally:
            if writer in self._connections:
                self._connections.remove(writer)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    def _on_frame(self, body: bytes, writer: asyncio.StreamWriter):
        msg_type = body[0]
        payload = body[1:]
        task = asyncio.create_task(self._dispatch(msg_type, payload, writer))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _dispatch(self, msg_type: int, payload: bytes, writer: asyncio.StreamWriter):
        if msg_type in (protocol.MSG_VERSION_REQUEST, protocol.MSG_WHOAMI):
            await self._send_frame(writer, protocol.MSG_VERSION_RESPONSE, json.dumps(self.identity).encode("utf-8"))
            return

        if msg_type == protocol.MSG_CMD_JSON:
            cmd = json.loads(payload.decode("utf-8"))
            self.command_log.append(cmd)
            cmd_type = cmd.get("type") or cmd.get("cmd") or ""
            seq = cmd.get("seq", 0)
            if cmd.get("wantAck", False):
                ack = {
                    "src": "mcu",
                    "cmd": cmd_type,
                    "seq": seq,
                    "ok": True,
                }
                ack.update(self.ack_overrides.get(cmd_type, {}))
                if cmd_type == "CMD_GPIO_READ":
                    ack.setdefault("channel", cmd.get("channel", 0))
                    ack.setdefault("value", 1)
                elif cmd_type == "CMD_ENCODER_READ":
                    ack.setdefault("encoder_id", cmd.get("encoder_id", 0))
                    ack.setdefault("ticks", 123)
                elif cmd_type == "CMD_ULTRASONIC_READ":
                    ack.setdefault("sensor_id", cmd.get("sensor_id", 0))
                    ack.setdefault("distance_cm", 42.5)
                elif cmd_type == "CMD_IMU_READ":
                    ack.setdefault("state", "ARMED")
                elif cmd_type == "CMD_SERVO_ATTACH":
                    ack.setdefault("servo_id", cmd.get("servo_id", 0))
                    ack.setdefault("channel", cmd.get("channel"))
                    ack.setdefault("pin", cmd.get("channel"))
                await self._send_frame(writer, protocol.MSG_CMD_JSON, json.dumps(ack).encode("utf-8"))

    async def _send_frame(self, writer: asyncio.StreamWriter, msg_type: int, payload: bytes = b""):
        writer.write(protocol.encode(msg_type, payload))
        await writer.drain()
