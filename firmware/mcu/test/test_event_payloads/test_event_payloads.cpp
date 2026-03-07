#include <unity.h>
#include "core/Event.h"


void setUp() {}
void tearDown() {}

void test_telemetry_struct_sanity() {
    TEST_ASSERT_EQUAL_UINT8(8, MAX_TELEMETRY_SERVOS);

    TelemetryServosPayload s{};
    s.num_channels = 3;
    s.angles[0] = 10.0f;
    s.angles[1] = 20.0f;
    s.angles[2] = 30.0f;

    TEST_ASSERT_EQUAL_UINT8(3, s.num_channels);
    TEST_ASSERT_FLOAT_WITHIN(0.0001f, 10.0f, s.angles[0]);
}

#ifdef ARDUINO
#include <Arduino.h>
void setup() {
    UNITY_BEGIN();
    RUN_TEST(test_telemetry_struct_sanity);
    UNITY_END();
}
void loop() {}
#else
int main(int, char**) {
    UNITY_BEGIN();
    RUN_TEST(test_telemetry_struct_sanity);
    return UNITY_END();
}
#endif
