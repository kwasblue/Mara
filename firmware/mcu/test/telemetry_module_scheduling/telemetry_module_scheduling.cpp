#include <unity.h>
#include <vector>
#include <cstdint>

#include "core/EventBus.h"
#include "core/Event.h"
#include "module/TelemetryModule.h"

static int g_bin_pub_count = 0;

static void capture(const Event& evt) {
    if (evt.type == EventType::BIN_MESSAGE_TX) {
        g_bin_pub_count++;
    }
}

void test_telemetry_interval_gating(void) {
    EventBus bus;
    TelemetryModule telem(bus);

    g_bin_pub_count = 0;
    bus.subscribe(&capture);

    telem.setBinaryEnabled(true);
    telem.setJsonEnabled(false);
    telem.setInterval(100);

    telem.registerBinProvider(1, [](std::vector<uint8_t>& out) {
        out.push_back(0x42);
    });

    telem.setup();

    telem.loop(0);
    telem.loop(50);
    TEST_ASSERT_EQUAL_INT(0, g_bin_pub_count);

    telem.loop(100);
    TEST_ASSERT_EQUAL_INT(1, g_bin_pub_count);

    telem.loop(150);
    TEST_ASSERT_EQUAL_INT(1, g_bin_pub_count);

    telem.loop(200);
    TEST_ASSERT_EQUAL_INT(2, g_bin_pub_count);
}

void test_telemetry_interval_zero_disables(void) {
    EventBus bus;
    TelemetryModule telem(bus);

    g_bin_pub_count = 0;
    bus.subscribe(&capture);

    telem.setBinaryEnabled(true);
    telem.setJsonEnabled(false);
    telem.setInterval(0);

    telem.registerBinProvider(1, [](std::vector<uint8_t>& out) {
        out.push_back(0x99);
    });

    telem.setup();

    telem.loop(0);
    telem.loop(1000);

    TEST_ASSERT_EQUAL_INT(0, g_bin_pub_count);
}

void setUp(void) {}
void tearDown(void) {}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_telemetry_interval_gating);
    RUN_TEST(test_telemetry_interval_zero_disables);
    return UNITY_END();
}
