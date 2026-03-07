import pytest
from mara_host.core import protocol


def test_encode_decode_roundtrip_single_frame():
    payload = b"hello"
    frame = protocol.encode(protocol.MSG_PING, payload)

    buf = bytearray(frame)
    bodies = []
    protocol.extract_frames(buf, lambda body: bodies.append(body))

    assert len(bodies) == 1
    body = bodies[0]
    assert body[0] == protocol.MSG_PING
    assert body[1:] == payload
    assert buf == bytearray()  # consumed


def test_extract_multiple_frames_with_noise_and_partial():
    frames = [
        protocol.encode(protocol.MSG_PING, b"a"),
        protocol.encode(protocol.MSG_PONG, b""),
        protocol.encode(protocol.MSG_CMD_JSON, b'{"x":1}'),
    ]

    noisy = b"\x00\x01\x02" + frames[0] + b"\x99" + frames[1] + frames[2]
    buf = bytearray(noisy)

    bodies = []
    protocol.extract_frames(buf, lambda body: bodies.append(body))

    assert [b[0] for b in bodies] == [protocol.MSG_PING, protocol.MSG_PONG, protocol.MSG_CMD_JSON]
    assert bodies[0][1:] == b"a"
    assert bodies[2][1:] == b'{"x":1}'
    assert len(buf) == 0


def test_bad_checksum_resync():
    good = protocol.encode(protocol.MSG_PING, b"abc")
    # corrupt one byte in payload
    bad = bytearray(good)
    bad[4] ^= 0xFF  # flip first payload byte
    bad = bytes(bad)

    buf = bytearray(bad + good)
    bodies = []
    protocol.extract_frames(buf, lambda body: bodies.append(body))

    # should skip bad one and still parse good
    assert len(bodies) == 1
    assert bodies[0][0] == protocol.MSG_PING
    assert bodies[0][1:] == b"abc"


def test_crc16_ccitt_known_values():
    """Verify CRC16-CCITT produces expected values for known inputs."""
    # Empty data with initial 0xFFFF
    assert protocol.crc16_ccitt(b"") == 0xFFFF

    # Known test vector: "123456789" should produce 0x29B1
    assert protocol.crc16_ccitt(b"123456789") == 0x29B1

    # Verify CRC changes with input
    crc1 = protocol.crc16_ccitt(b"abc")
    crc2 = protocol.crc16_ccitt(b"abd")
    assert crc1 != crc2  # Different inputs produce different CRCs


def test_frame_format_has_2_byte_crc():
    """Verify the frame format uses 2-byte CRC at the end."""
    payload = b"test"
    frame = protocol.encode(protocol.MSG_CMD_JSON, payload)

    # Frame: HEADER(1) + len_hi(1) + len_lo(1) + msg_type(1) + payload(4) + crc(2) = 10 bytes
    assert len(frame) == 10

    # Verify header
    assert frame[0] == protocol.HEADER

    # Verify length field (1 + len(payload) = 5)
    length = (frame[1] << 8) | frame[2]
    assert length == 5

    # Verify msg_type
    assert frame[3] == protocol.MSG_CMD_JSON

    # Verify payload
    assert frame[4:8] == payload

    # Verify CRC (last 2 bytes)
    crc_hi = frame[8]
    crc_lo = frame[9]
    recv_crc = (crc_hi << 8) | crc_lo

    # Calculate expected CRC
    expected_crc = protocol.crc16_ccitt(bytes([frame[1], frame[2], frame[3]]) + payload)
    assert recv_crc == expected_crc


def test_empty_payload_frame():
    """Test frame with no payload."""
    frame = protocol.encode(protocol.MSG_HEARTBEAT, b"")

    # Frame: HEADER(1) + len(2) + msg_type(1) + crc(2) = 6 bytes
    assert len(frame) == 6

    buf = bytearray(frame)
    bodies = []
    protocol.extract_frames(buf, lambda body: bodies.append(body))

    assert len(bodies) == 1
    assert bodies[0][0] == protocol.MSG_HEARTBEAT
    assert bodies[0][1:] == b""
