#include <unity.h>
#include <vector>
#include <cstdint>

#include "core/EventBus.h"
#include "core/Event.h"
#include "module/TelemetryModule.h"

// ---- capture helper ----
static bool  g_has_evt = false;
static Event g_last_evt{};

static void capture_evt(const Event& evt) {
    g_last_evt = evt;   // copies strings/vectors safely
    g_has_evt = true;
}

static uint16_t le_u16(const std::vector<uint8_t>& b, size_t off) {
    return static_cast<uint16_t>(b[off] | (static_cast<uint16_t>(b[off + 1]) << 8));
}

static uint32_t le_u32(const std::vector<uint8_t>& b, size_t off) {
    return static_cast<uint32_t>(b[off] |
        (static_cast<uint32_t>(b[off + 1]) << 8) |
        (static_cast<uint32_t>(b[off + 2]) << 16) |
        (static_cast<uint32_t>(b[off + 3]) << 24));
}

void setUp() {
    g_has_evt = false;
    g_last_evt = Event{};
}

void tearDown() {}

void test_telemetry_module_emits_bin_payload_layout() {
    EventBus bus;
    bus.subscribe(capture_evt);

    TelemetryModule tm(bus);
    tm.setInterval(1);
    tm.setBinaryEnabled(true);
    tm.setJsonEnabled(false);

    // Register two bin providers, deterministic bytes
    tm.registerBinProvider(1, [](std::vector<uint8_t>& out) {
        out.push_back(0xAA);
        out.push_back(0xBB);
    });

    tm.registerBinProvider(2, [](std::vector<uint8_t>& out) {
        out.push_back(0x01);
    });

    // Force a tick
    tm.loop(100);

    TEST_ASSERT_TRUE_MESSAGE(g_has_evt, "Expected an event to be published");
    TEST_ASSERT_EQUAL(EventType::BIN_MESSAGE_TX, g_last_evt.type);

    const auto& p = g_last_evt.payload.bin;

    // Payload format (from your TelemetryModule.cpp):
    //   u8 version (=1)
    //   u16 seq
    //   u32 ts_ms
    //   u8 section_count
    //   sections...

    TEST_ASSERT_TRUE_MESSAGE(p.size() >= 8, "Payload too small");

    const uint8_t ver = p[0];
    const uint16_t seq = le_u16(p, 1);
    const uint32_t ts  = le_u32(p, 3);
    const uint8_t section_count = p[7];

    TEST_ASSERT_EQUAL_UINT8(1, ver);
    TEST_ASSERT_EQUAL_UINT16(0, seq);      // first packet seq_ starts at 0
    TEST_ASSERT_EQUAL_UINT32(100, ts);
    TEST_ASSERT_EQUAL_UINT8(2, section_count);

    // Walk sections
    size_t off = 8;

    // Section 1
    TEST_ASSERT_TRUE_MESSAGE(off + 3 <= p.size(), "Section 1 header out of range");
    uint8_t sid1 = p[off + 0];
    uint16_t len1 = le_u16(p, off + 1);
    off += 3;
    TEST_ASSERT_EQUAL_UINT8(1, sid1);
    TEST_ASSERT_EQUAL_UINT16(2, len1);
    TEST_ASSERT_TRUE_MESSAGE(off + len1 <= p.size(), "Section 1 data out of range");
    TEST_ASSERT_EQUAL_UINT8(0xAA, p[off + 0]);
    TEST_ASSERT_EQUAL_UINT8(0xBB, p[off + 1]);
    off += len1;

    // Section 2
    TEST_ASSERT_TRUE_MESSAGE(off + 3 <= p.size(), "Section 2 header out of range");
    uint8_t sid2 = p[off + 0];
    uint16_t len2 = le_u16(p, off + 1);
    off += 3;
    TEST_ASSERT_EQUAL_UINT8(2, sid2);
    TEST_ASSERT_EQUAL_UINT16(1, len2);
    TEST_ASSERT_TRUE_MESSAGE(off + len2 <= p.size(), "Section 2 data out of range");
    TEST_ASSERT_EQUAL_UINT8(0x01, p[off + 0]);
    off += len2;

    // No trailing junk
    TEST_ASSERT_EQUAL_UINT32(p.size(), off);
}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_telemetry_module_emits_bin_payload_layout);
    return UNITY_END();
}

// Arduino Unity hooks
void setup() { (void)main(0, nullptr); }
void loop() {}
