#pragma once
#include <cstdint>
#include <vector>
#include <functional>

namespace Protocol {

static constexpr uint8_t HEADER = 0xAA;

enum MsgType : uint8_t {
    MSG_HEARTBEAT        = 0x01,
    MSG_PING             = 0x02,
    MSG_PONG             = 0x03,
    MSG_VERSION_REQUEST  = 0x04,
    MSG_VERSION_RESPONSE = 0x05,
    MSG_WHOAMI           = 0x10,
    MSG_TELEMETRY_BIN    = 0x30,
    MSG_CMD_JSON         = 0x50,
    MSG_CMD_BIN          = 0x51,  // Binary command for high-rate streaming
};

// -----------------------------------------------------------------------------
// CRC16-CCITT (polynomial 0x1021, initial 0xFFFF)
// Provides much stronger error detection than simple sum checksum
// -----------------------------------------------------------------------------
inline uint16_t crc16_ccitt(const uint8_t* data, size_t len, uint16_t crc = 0xFFFF) {
    for (size_t i = 0; i < len; ++i) {
        crc ^= static_cast<uint16_t>(data[i]) << 8;
        for (uint8_t bit = 0; bit < 8; ++bit) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

// Convenience: CRC a single byte (for incremental calculation)
inline uint16_t crc16_ccitt_byte(uint8_t byte, uint16_t crc = 0xFFFF) {
    return crc16_ccitt(&byte, 1, crc);
}

// -----------------------------------------------------------------------------
// Encode: [HEADER][len_hi][len_lo][msgType][payload...][crc_hi][crc_lo]
// length = 1 + payloadLen  (bytes in [msgType][payload...])
// CRC16 is calculated over: len_hi, len_lo, msgType, payload
// -----------------------------------------------------------------------------
inline void encode(uint8_t msgType,
                   const uint8_t* payload,
                   size_t payloadLen,
                   std::vector<uint8_t>& outFrame)
{
    outFrame.clear();

    uint16_t length = static_cast<uint16_t>(1 + payloadLen);

    uint8_t len_hi = static_cast<uint8_t>((length >> 8) & 0xFF);
    uint8_t len_lo = static_cast<uint8_t>(length & 0xFF);

    // Calculate CRC16 over length bytes + msgType + payload
    uint16_t crc = 0xFFFF;
    crc = crc16_ccitt_byte(len_hi, crc);
    crc = crc16_ccitt_byte(len_lo, crc);
    crc = crc16_ccitt_byte(msgType, crc);
    crc = crc16_ccitt(payload, payloadLen, crc);

    outFrame.reserve(1 + 2 + 1 + payloadLen + 2);

    outFrame.push_back(HEADER);
    outFrame.push_back(len_hi);
    outFrame.push_back(len_lo);
    outFrame.push_back(msgType);

    for (size_t i = 0; i < payloadLen; ++i) {
        outFrame.push_back(payload[i]);
    }

    outFrame.push_back(static_cast<uint8_t>((crc >> 8) & 0xFF));
    outFrame.push_back(static_cast<uint8_t>(crc & 0xFF));
}

// -----------------------------------------------------------------------------
// Decode: [HEADER][len_hi][len_lo][msgType][payload...][crc_hi][crc_lo]
// Calls onFrame(body, length) where:
//     body[0] = msgType
//     body[1..length-1] = payload
// -----------------------------------------------------------------------------
inline void extractFrames(std::vector<uint8_t>& buffer,
                          const std::function<void(const uint8_t* frame, size_t len)>& onFrame)
{
    size_t i = 0;
    constexpr size_t MIN_FRAME_HEADER = 6;  // HEADER + len(2) + msgType + crc(2)

    while (i + MIN_FRAME_HEADER <= buffer.size()) {
        if (buffer[i] != HEADER) {
            ++i;
            continue;
        }

        if (i + 3 > buffer.size()) {
            break;
        }

        uint8_t len_hi = buffer[i + 1];
        uint8_t len_lo = buffer[i + 2];
        uint16_t length = static_cast<uint16_t>((len_hi << 8) | len_lo);

        if (length < 1) {
            ++i;
            continue;
        }

        // Frame total: HEADER(1) + len(2) + body(length) + crc(2)
        size_t frameTotal = 1 + 2 + static_cast<size_t>(length) + 2;

        if (i + frameTotal > buffer.size()) {
            break;
        }

        const uint8_t* body = &buffer[i + 3];
        uint8_t msgType = body[0];
        const uint8_t* payload = &body[1];
        size_t payloadLen = static_cast<size_t>(length) - 1;

        // Extract received CRC (big-endian)
        uint8_t crc_hi = buffer[i + 3 + length];
        uint8_t crc_lo = buffer[i + 3 + length + 1];
        uint16_t recvCrc = static_cast<uint16_t>((crc_hi << 8) | crc_lo);

        // Calculate expected CRC over: len_hi, len_lo, msgType, payload
        uint16_t crc = 0xFFFF;
        crc = crc16_ccitt_byte(len_hi, crc);
        crc = crc16_ccitt_byte(len_lo, crc);
        crc = crc16_ccitt_byte(msgType, crc);
        crc = crc16_ccitt(payload, payloadLen, crc);

        if (crc == recvCrc) {
            onFrame(body, static_cast<size_t>(length));
            i += frameTotal;
        } else {
            ++i;
        }
    }

    if (i > 0) {
        buffer.erase(buffer.begin(), buffer.begin() + static_cast<long>(i));
    }
}

} // namespace Protocol