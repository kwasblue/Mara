# tests/fakes/fake_async_transport.py

import json
from mara_host.core import protocol


class FakeAsyncTransport:
    def __init__(self, auto_ack: bool = True):
        self._handler = None
        self._auto_ack = auto_ack
        self._sent = []

    def set_frame_handler(self, handler):
        self._handler = handler
        
    def start(self):
        pass

    def stop(self):
        pass

    async def send_bytes(self, data: bytes) -> None:
        self._sent.append(data)
        
        # Auto-ack JSON commands if enabled
        if self._auto_ack and len(data) > 4:
            msg_type = data[3]  # After HEADER, len_hi, len_lo
            if msg_type == protocol.MSG_CMD_JSON:
                await self._auto_ack_json_cmd(data)

    async def _auto_ack_json_cmd(self, frame_data: bytes) -> None:
        try:
            length = (frame_data[1] << 8) | frame_data[2]
            payload = frame_data[4:4 + length - 1]
            msg = json.loads(payload.decode("utf-8"))

            cmd_name = msg.get("cmd") or msg.get("type") or ""
            seq = msg.get("seq", 0)

            ack = {
                "src": "mcu",
                "cmd": cmd_name,   
                "seq": seq,
                "ok": True,
            }
            await self._inject_json_from_mcu(ack)
        except Exception as e:
            # DON'T swallow while debugging
            print(f"[FakeAsyncTransport] auto-ack failed: {e}")


    def _inject_body(self, body: bytes) -> None:
        """Inject raw body (msg_type + payload) into handler."""
        if self._handler:
            self._handler(body)

    async def inject_pong(self) -> None:
        """Inject a PONG frame."""
        self._inject_body(bytes([protocol.MSG_PONG]))

    async def inject_heartbeat(self) -> None:
        """Inject a HEARTBEAT frame."""
        self._inject_body(bytes([protocol.MSG_HEARTBEAT]))

    async def inject_raw(self, msg_type: int, payload: bytes) -> None:
        """Inject an arbitrary frame."""
        self._inject_body(bytes([msg_type]) + payload)

    async def _inject_version_response(self, data: dict) -> None:
        """Inject a VERSION_RESPONSE frame."""
        payload = json.dumps(data).encode("utf-8")
        self._inject_body(bytes([protocol.MSG_VERSION_RESPONSE]) + payload)

    async def _inject_json_from_mcu(self, data: dict) -> None:
        """Inject a CMD_JSON frame."""
        payload = json.dumps(data).encode("utf-8")
        self._inject_body(bytes([protocol.MSG_CMD_JSON]) + payload)