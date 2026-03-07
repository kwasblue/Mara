import pytest
from mara_host.transport.base_transport import BaseTransport
from mara_host.core import protocol


class DummyTransport(BaseTransport):
    def __init__(self):
        super().__init__()
        self.sent = []
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def _send_bytes(self, data: bytes) -> None:
        self.sent.append(data)


def test_base_transport_send_frame_encodes():
    t = DummyTransport()
    t.send_frame(protocol.MSG_PING, b"hi")

    assert len(t.sent) == 1
    frame = t.sent[0]

    buf = bytearray(frame)
    bodies = []
    protocol.extract_frames(buf, lambda body: bodies.append(body))

    assert len(bodies) == 1
    assert bodies[0][0] == protocol.MSG_PING
    assert bodies[0][1:] == b"hi"
