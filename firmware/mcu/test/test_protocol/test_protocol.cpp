// test/test_protocol/test_protocol.cpp
#include <unity.h>
#include <vector>
#include <cstdint>
#include <cstring>

// IMPORTANT: In PlatformIO, `include/` is already on the include path.
// So you should include headers relative to include/, like:
#include "core/Protocol.h"

using Protocol::HEADER;

// ---------------- Helpers ----------------

// CRC16 helper for tests - mirrors Protocol::crc16_ccitt
static uint16_t crc16_for(uint16_t length, uint8_t msgType, const uint8_t* payload, size_t payloadLen) {
    uint8_t len_hi = static_cast<uint8_t>((length >> 8) & 0xFF);
    uint8_t len_lo = static_cast<uint8_t>(length & 0xFF);

    uint16_t crc = 0xFFFF;
    crc = Protocol::crc16_ccitt_byte(len_hi, crc);
    crc = Protocol::crc16_ccitt_byte(len_lo, crc);
    crc = Protocol::crc16_ccitt_byte(msgType, crc);
    crc = Protocol::crc16_ccitt(payload, payloadLen, crc);
    return crc;
}

struct CapturedFrame {
    std::vector<uint8_t> body; // msgType + payload
};

static void push_bytes(std::vector<uint8_t>& buf, const std::vector<uint8_t>& more) {
    buf.insert(buf.end(), more.begin(), more.end());
}

static void push_bytes(std::vector<uint8_t>& buf, const uint8_t* data, size_t n) {
    buf.insert(buf.end(), data, data + n);
}

// ---------------- Tests ----------------

void test_encode_builds_expected_frame() {
    const uint8_t msgType = 0x50; // example (CMD_JSON)
    const uint8_t payload[] = {0x10, 0x20, 0x30, 0x40};
    const size_t payloadLen = sizeof(payload);

    std::vector<uint8_t> frame;
    Protocol::encode(msgType, payload, payloadLen, frame);

    // Frame size = HEADER(1) + len(2) + msgType(1) + payload + crc(2)
    TEST_ASSERT_EQUAL_UINT32((uint32_t)(1 + 2 + 1 + payloadLen + 2), (uint32_t)frame.size());
    TEST_ASSERT_EQUAL_UINT8(HEADER, frame[0]);

    const uint16_t length = static_cast<uint16_t>(1 + payloadLen);
    TEST_ASSERT_EQUAL_UINT8((length >> 8) & 0xFF, frame[1]);
    TEST_ASSERT_EQUAL_UINT8(length & 0xFF, frame[2]);

    TEST_ASSERT_EQUAL_UINT8(msgType, frame[3]);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, &frame[4], payloadLen);

    const uint16_t expectedCrc = crc16_for(length, msgType, payload, payloadLen);
    TEST_ASSERT_EQUAL_UINT8((expectedCrc >> 8) & 0xFF, frame[4 + payloadLen]);
    TEST_ASSERT_EQUAL_UINT8(expectedCrc & 0xFF, frame[4 + payloadLen + 1]);
}

void test_extract_single_frame() {
    const uint8_t msgType = 0x02; // PING
    const uint8_t payload[] = {0xAB, 0xCD};
    const size_t payloadLen = sizeof(payload);

    std::vector<uint8_t> frame;
    Protocol::encode(msgType, payload, payloadLen, frame);

    std::vector<uint8_t> buffer;
    push_bytes(buffer, frame);

    std::vector<CapturedFrame> got;
    Protocol::extractFrames(buffer, [&](const uint8_t* body, size_t len) {
        CapturedFrame f;
        f.body.assign(body, body + len);
        got.push_back(std::move(f));
    });

    TEST_ASSERT_EQUAL_INT(1, (int)got.size());
    TEST_ASSERT_EQUAL_UINT8(msgType, got[0].body[0]);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, &got[0].body[1], payloadLen);

    // buffer should be empty after consuming the frame
    TEST_ASSERT_TRUE(buffer.empty());
}

void test_extract_ignores_noise_before_header() {
    const uint8_t msgType = 0x03; // PONG
    const uint8_t payload[] = {0x01};
    const size_t payloadLen = sizeof(payload);

    std::vector<uint8_t> frame;
    Protocol::encode(msgType, payload, payloadLen, frame);

    std::vector<uint8_t> buffer = {0x00, 0x11, 0x22, 0x33}; // noise
    push_bytes(buffer, frame);

    std::vector<CapturedFrame> got;
    Protocol::extractFrames(buffer, [&](const uint8_t* body, size_t len) {
        CapturedFrame f;
        f.body.assign(body, body + len);
        got.push_back(std::move(f));
    });

    TEST_ASSERT_EQUAL_INT(1, (int)got.size());
    TEST_ASSERT_EQUAL_UINT8(msgType, got[0].body[0]);
    TEST_ASSERT_EQUAL_UINT8(payload[0], got[0].body[1]);
    TEST_ASSERT_TRUE(buffer.empty());
}

void test_extract_partial_frame_buffering() {
    const uint8_t msgType = 0x50; // CMD_JSON
    const uint8_t payload[] = {0xDE, 0xAD, 0xBE, 0xEF, 0x01};
    const size_t payloadLen = sizeof(payload);

    std::vector<uint8_t> frame;
    Protocol::encode(msgType, payload, payloadLen, frame);

    std::vector<uint8_t> buffer;
    std::vector<CapturedFrame> got;

    // Feed in two chunks: first chunk is not enough for full frame
    push_bytes(buffer, frame.data(), 3); // HEADER + len_hi + len_lo only
    Protocol::extractFrames(buffer, [&](const uint8_t* body, size_t len) {
        CapturedFrame f; f.body.assign(body, body + len); got.push_back(std::move(f));
    });
    TEST_ASSERT_EQUAL_INT(0, (int)got.size());
    TEST_ASSERT_EQUAL_UINT32((uint32_t)frame.size(), (uint32_t)frame.size()); // still waiting

    // Feed rest
    push_bytes(buffer, frame.data() + 3, frame.size() - 3);
    Protocol::extractFrames(buffer, [&](const uint8_t* body, size_t len) {
        CapturedFrame f; f.body.assign(body, body + len); got.push_back(std::move(f));
    });

    TEST_ASSERT_EQUAL_INT(1, (int)got.size());
    TEST_ASSERT_EQUAL_UINT8(msgType, got[0].body[0]);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, &got[0].body[1], payloadLen);
    TEST_ASSERT_TRUE(buffer.empty());
}

void test_extract_back_to_back_frames() {
    const uint8_t msgType1 = 0x01; // HEARTBEAT
    const uint8_t payload1[] = {0xAA};
    const size_t payloadLen1 = sizeof(payload1);

    const uint8_t msgType2 = 0x10; // WHOAMI
    const uint8_t payload2[] = {0x01, 0x02, 0x03};
    const size_t payloadLen2 = sizeof(payload2);

    std::vector<uint8_t> f1, f2;
    Protocol::encode(msgType1, payload1, payloadLen1, f1);
    Protocol::encode(msgType2, payload2, payloadLen2, f2);

    std::vector<uint8_t> buffer;
    push_bytes(buffer, f1);
    push_bytes(buffer, f2);

    std::vector<CapturedFrame> got;
    Protocol::extractFrames(buffer, [&](const uint8_t* body, size_t len) {
        CapturedFrame f; f.body.assign(body, body + len); got.push_back(std::move(f));
    });

    TEST_ASSERT_EQUAL_INT(2, (int)got.size());

    TEST_ASSERT_EQUAL_UINT8(msgType1, got[0].body[0]);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(payload1, &got[0].body[1], payloadLen1);

    TEST_ASSERT_EQUAL_UINT8(msgType2, got[1].body[0]);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(payload2, &got[1].body[1], payloadLen2);

    TEST_ASSERT_TRUE(buffer.empty());
}

void test_extract_bad_checksum_resyncs_to_next_frame() {
    const uint8_t msgType1 = 0x50;
    const uint8_t payload1[] = {0x10, 0x20};
    const size_t payloadLen1 = sizeof(payload1);

    const uint8_t msgType2 = 0x02; // PING
    const uint8_t payload2[] = {0x99};
    const size_t payloadLen2 = sizeof(payload2);

    std::vector<uint8_t> f1, f2;
    Protocol::encode(msgType1, payload1, payloadLen1, f1);
    Protocol::encode(msgType2, payload2, payloadLen2, f2);

    // Corrupt checksum of f1
    f1[f1.size() - 1] ^= 0xFF;

    std::vector<uint8_t> buffer;
    push_bytes(buffer, f1);
    push_bytes(buffer, f2);

    std::vector<CapturedFrame> got;
    Protocol::extractFrames(buffer, [&](const uint8_t* body, size_t len) {
        CapturedFrame f; f.body.assign(body, body + len); got.push_back(std::move(f));
    });

    // Should drop f1 and still decode f2
    TEST_ASSERT_EQUAL_INT(1, (int)got.size());
    TEST_ASSERT_EQUAL_UINT8(msgType2, got[0].body[0]);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(payload2, &got[0].body[1], payloadLen2);
    TEST_ASSERT_TRUE(buffer.empty());
}

void test_extract_false_header_invalid_length_does_not_consume_valid_frame() {
    // Construct: [HEADER][0x00][0x00] => length=0 (invalid), then a valid frame
    std::vector<uint8_t> buffer = {HEADER, 0x00, 0x00};

    const uint8_t msgType = 0x03; // PONG
    const uint8_t payload[] = {0x55, 0x66};
    const size_t payloadLen = sizeof(payload);

    std::vector<uint8_t> good;
    Protocol::encode(msgType, payload, payloadLen, good);
    push_bytes(buffer, good);

    std::vector<CapturedFrame> got;
    Protocol::extractFrames(buffer, [&](const uint8_t* body, size_t len) {
        CapturedFrame f; f.body.assign(body, body + len); got.push_back(std::move(f));
    });

    TEST_ASSERT_EQUAL_INT(1, (int)got.size());
    TEST_ASSERT_EQUAL_UINT8(msgType, got[0].body[0]);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, &got[0].body[1], payloadLen);
    TEST_ASSERT_TRUE(buffer.empty());
}

void test_extract_leaves_unconsumed_trailing_bytes() {
    const uint8_t msgType = 0x02; // PING
    const uint8_t payload[] = {0x01, 0x02, 0x03};
    const size_t payloadLen = sizeof(payload);

    std::vector<uint8_t> frame;
    Protocol::encode(msgType, payload, payloadLen, frame);

    std::vector<uint8_t> buffer;
    push_bytes(buffer, frame);

    // Add trailing garbage that is not a full frame yet
    buffer.push_back(HEADER); // start of possible next frame, but incomplete
    buffer.push_back(0x00);

    std::vector<CapturedFrame> got;
    Protocol::extractFrames(buffer, [&](const uint8_t* body, size_t len) {
        CapturedFrame f; f.body.assign(body, body + len); got.push_back(std::move(f));
    });

    TEST_ASSERT_EQUAL_INT(1, (int)got.size());
    TEST_ASSERT_EQUAL_UINT8(msgType, got[0].body[0]);

    // should leave the trailing bytes
    TEST_ASSERT_EQUAL_UINT32((uint32_t)frame.size(), (uint32_t)frame.size());
    TEST_ASSERT_EQUAL_UINT8(HEADER, buffer[0]);
    TEST_ASSERT_EQUAL_UINT8(0x00, buffer[1]);
}

void test_crc16_ccitt_known_test_vector() {
    // Standard CRC16-CCITT test vector: "123456789" should produce 0x29B1
    // This must match the Python implementation for interoperability
    const uint8_t data[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    uint16_t crc = Protocol::crc16_ccitt(data, sizeof(data));
    TEST_ASSERT_EQUAL_HEX16(0x29B1, crc);
}

void test_crc16_empty_input() {
    // Empty data with initial 0xFFFF should return 0xFFFF
    uint16_t crc = Protocol::crc16_ccitt(nullptr, 0);
    TEST_ASSERT_EQUAL_HEX16(0xFFFF, crc);
}

void test_frame_interop_with_python() {
    // Verify frame format matches Python implementation
    // Python: encode(MSG_PING, b"hello") produces frame with specific CRC
    const uint8_t msgType = Protocol::MSG_PING;  // 0x02
    const uint8_t payload[] = {'h', 'e', 'l', 'l', 'o'};
    const size_t payloadLen = sizeof(payload);

    std::vector<uint8_t> frame;
    Protocol::encode(msgType, payload, payloadLen, frame);

    // Frame should be: AA 00 06 02 68 65 6c 6c 6f D8 39
    // (Python verified: d839 is the CRC)
    TEST_ASSERT_EQUAL_UINT32(11, (uint32_t)frame.size());
    TEST_ASSERT_EQUAL_UINT8(0xAA, frame[0]);      // HEADER
    TEST_ASSERT_EQUAL_UINT8(0x00, frame[1]);      // len_hi
    TEST_ASSERT_EQUAL_UINT8(0x06, frame[2]);      // len_lo (1 + 5)
    TEST_ASSERT_EQUAL_UINT8(0x02, frame[3]);      // MSG_PING
    TEST_ASSERT_EQUAL_UINT8('h', frame[4]);
    TEST_ASSERT_EQUAL_UINT8('e', frame[5]);
    TEST_ASSERT_EQUAL_UINT8('l', frame[6]);
    TEST_ASSERT_EQUAL_UINT8('l', frame[7]);
    TEST_ASSERT_EQUAL_UINT8('o', frame[8]);
    TEST_ASSERT_EQUAL_UINT8(0xD8, frame[9]);      // CRC hi
    TEST_ASSERT_EQUAL_UINT8(0x39, frame[10]);     // CRC lo
}

// ---------------- Cross-platform test runner ----------------

void setUp() {}
void tearDown() {}

#include "../test_runner.h"

void run_tests() {
    RUN_TEST(test_encode_builds_expected_frame);
    RUN_TEST(test_extract_single_frame);
    RUN_TEST(test_extract_ignores_noise_before_header);
    RUN_TEST(test_extract_partial_frame_buffering);
    RUN_TEST(test_extract_back_to_back_frames);
    RUN_TEST(test_extract_bad_checksum_resyncs_to_next_frame);
    RUN_TEST(test_extract_false_header_invalid_length_does_not_consume_valid_frame);
    RUN_TEST(test_extract_leaves_unconsumed_trailing_bytes);
    // CRC16 verification tests
    RUN_TEST(test_crc16_ccitt_known_test_vector);
    RUN_TEST(test_crc16_empty_input);
    RUN_TEST(test_frame_interop_with_python);
}

TEST_RUNNER(run_tests)
