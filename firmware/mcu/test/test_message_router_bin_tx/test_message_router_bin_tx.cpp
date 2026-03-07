#include <unity.h>
#include <vector>
#include <cstdint>

#include "core/EventBus.h"
#include "core/Event.h"
#include "command/MessageRouter.h"
#include "core/Protocol.h"
#include "test/fakes/FakeTransport.h"

static uint8_t checksum_for(uint16_t length, uint8_t msgType, const std::vector<uint8_t>& payload) {
    uint32_t sum = length + msgType;
    for (auto b : payload) sum += b;
    return static_cast<uint8_t>(sum & 0xFF);
}

void setUp() {}
void tearDown() {}

void test_router_forwards_bin_message_tx_as_telem_bin_frame() {
    EventBus bus;
    FakeTransport transport;

    MessageRouter router(bus, transport);
    router.setup();

    // Build a fake binary telemetry payload
    std::vector<uint8_t> bin_payload = {0x01, 0x02, 0x03, 0x04};

    Event evt;
    evt.type = EventType::BIN_MESSAGE_TX;
    evt.timestamp_ms = 123;
    evt.payload = {};
    evt.payload.bin = bin_payload;

    bus.publish(evt);

    TEST_ASSERT_EQUAL_INT_MESSAGE(1, transport.sendCount, "Expected router to send exactly one frame");
    TEST_ASSERT_TRUE_MESSAGE(transport.tx.size() >= 5, "Frame too small");

    // Protocol frame layout:
    // [HEADER][len_hi][len_lo][msgType][payload...][checksum]
    TEST_ASSERT_EQUAL_UINT8(Protocol::HEADER, transport.tx[0]);

    uint16_t length = static_cast<uint16_t>((transport.tx[1] << 8) | transport.tx[2]);
    uint8_t  msgType = transport.tx[3];

    TEST_ASSERT_EQUAL_UINT8(Protocol::MSG_TELEMETRY_BIN, msgType);

    // length = 1 + payloadLen
    TEST_ASSERT_EQUAL_UINT16(1 + bin_payload.size(), length);

    // payload begins at index 4
    size_t payloadLen = length - 1;
    TEST_ASSERT_EQUAL_UINT32(bin_payload.size(), payloadLen);

    for (size_t i = 0; i < payloadLen; ++i) {
        TEST_ASSERT_EQUAL_UINT8(bin_payload[i], transport.tx[4 + i]);
    }

    uint8_t recv_checksum = transport.tx[4 + payloadLen];
    uint8_t exp_checksum = checksum_for(length, msgType, bin_payload);
    TEST_ASSERT_EQUAL_UINT8(exp_checksum, recv_checksum);
}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_router_forwards_bin_message_tx_as_telem_bin_frame);
    return UNITY_END();
}

void setup() { (void)main(0, nullptr); }
void loop() {}
