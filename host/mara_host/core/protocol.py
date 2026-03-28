from typing import Callable

HEADER = 0xAA

MSG_HEARTBEAT        = 0x01
MSG_PING             = 0x02
MSG_PONG             = 0x03
MSG_VERSION_REQUEST  = 0x04
MSG_VERSION_RESPONSE = 0x05
MSG_WHOAMI           = 0x10
MSG_TELEMETRY_BIN    = 0x30
MSG_CMD_JSON         = 0x50
MSG_CMD_BIN          = 0x51  # Binary command for high-rate streaming

_MAX_LEN = 4096  # Maximum payload size to prevent DoS (matches firmware)


# Pre-computed CRC16-CCITT lookup table (polynomial 0x1021)
# ~7x faster than bit-by-bit calculation
def _make_crc16_table() -> tuple:
    """Build CRC16-CCITT lookup table at module load time."""
    table = []
    for i in range(256):
        crc = i << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
        table.append(crc)
    return tuple(table)

_CRC16_TABLE = _make_crc16_table()


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    """
    CRC16-CCITT (polynomial 0x1021, initial 0xFFFF).
    Uses lookup table for ~10x speedup over bit-by-bit.
    """
    table = _CRC16_TABLE  # Local reference for faster lookup
    for byte in data:
        crc = ((crc << 8) ^ table[((crc >> 8) ^ byte) & 0xFF]) & 0xFFFF
    return crc


def encode(msg_type: int, payload: bytes = b"") -> bytes:
    """
    Encode a frame as:
        [HEADER][len_hi][len_lo][msg_type][payload...][crc_hi][crc_lo]

    where:
        length = 1 + len(payload)  # msg_type + payload
        CRC16 is calculated over: len_hi, len_lo, msg_type, payload
    """
    length = 1 + len(payload)
    if length <= 0 or length > _MAX_LEN:
        raise ValueError(f"Invalid frame length: {length}")

    len_hi = (length >> 8) & 0xFF
    len_lo = length & 0xFF

    # Calculate CRC16 over: len_hi, len_lo, msg_type, payload
    crc = crc16_ccitt(bytes([len_hi, len_lo, msg_type]) + payload)
    crc_hi = (crc >> 8) & 0xFF
    crc_lo = crc & 0xFF

    # Pre-allocate exact frame size (1 extra byte for 2-byte CRC vs 1-byte checksum)
    payload_len = len(payload)
    frame = bytearray(6 + payload_len)  # header + len_hi + len_lo + msg_type + payload + crc(2)
    frame[0] = HEADER
    frame[1] = len_hi
    frame[2] = len_lo
    frame[3] = msg_type
    if payload_len > 0:
        frame[4:4 + payload_len] = payload
    frame[4 + payload_len] = crc_hi
    frame[5 + payload_len] = crc_lo
    return bytes(frame)


_HEADER_BYTE = bytes([HEADER])  # Pre-allocated for find()

def extract_frames(buffer: bytearray, on_frame: Callable[[bytes], None]) -> None:
    """
    Parse as many frames as possible from buffer.

    Frame format:
        [HEADER][len_hi][len_lo][msg_type][payload...][crc_hi][crc_lo]

    Calls:
        on_frame(body)
    where:
        body[0] = msg_type
        body[1:] = payload

    Mutates buffer, removing consumed bytes.
    """

    i = 0
    n = len(buffer)

    # need at least HEADER + len_hi + len_lo + msg_type + crc(2)
    MIN_FRAME_HEADER = 1 + 2 + 1 + 2  # header + len_hi/lo + msg_type + crc(2)

    while i + MIN_FRAME_HEADER <= n:
        # Vectorized search for HEADER byte (faster than byte-by-byte)
        if buffer[i] != HEADER:
            idx = buffer.find(_HEADER_BYTE, i)
            if idx == -1:
                # No header found in rest of buffer
                i = n
                break
            i = idx
            if i + MIN_FRAME_HEADER > n:
                break

        # need at least HEADER + len_hi + len_lo
        if i + 3 > n:
            break

        len_hi = buffer[i + 1]
        len_lo = buffer[i + 2]
        length = (len_hi << 8) | len_lo  # length of [msg_type][payload...]

        # sanity check
        if length < 1 or length > _MAX_LEN:
            # bogus length -> treat as false header, resync
            i += 1
            continue

        # total frame size:
        #   HEADER(1) + len_hi(1) + len_lo(1) + body(length) + crc(2)
        frame_total = 1 + 2 + length + 2

        if i + frame_total > n:
            # not enough data yet
            break

        # body = [msg_type][payload...]
        body_start = i + 3
        body_end   = body_start + length
        body = buffer[body_start:body_end]

        if not body:
            # should not happen if length >= 1, but be defensive
            i += 1
            continue

        msg_type = body[0]
        payload  = body[1:]

        # Extract received CRC (big-endian)
        recv_crc_hi = buffer[body_end]
        recv_crc_lo = buffer[body_end + 1]
        recv_crc = (recv_crc_hi << 8) | recv_crc_lo

        # Calculate expected CRC over: len_hi, len_lo, msg_type, payload
        expected_crc = crc16_ccitt(bytes([len_hi, len_lo, msg_type]) + payload)

        if expected_crc == recv_crc:
            # good frame
            on_frame(bytes(body))  # msg_type + payload
            i += frame_total
        else:
            # bad frame, skip this HEADER and resync
            i += 1

        n = len(buffer)

    if i > 0:
        del buffer[:i]
