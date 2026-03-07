#include <unity.h>
#include "control/SignalBus.h"

// Include implementation for native build
#include "../../src/core/SignalBus.cpp"

static SignalBus bus;

void setUp() { bus.clear(); }
void tearDown() {}

void test_define_and_get() {
    TEST_ASSERT_TRUE(bus.define(100, "ref", SignalBus::Kind::REF, 5.0f));
    float val;
    TEST_ASSERT_TRUE(bus.get(100, val));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 5.0f, val);
}

void test_set_updates_value() {
    bus.define(100, "ref", SignalBus::Kind::REF, 0.0f);
    bus.set(100, 10.0f, 1000);
    float val;
    bus.get(100, val);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 10.0f, val);
}

void test_get_nonexistent_returns_false() {
    float val;
    TEST_ASSERT_FALSE(bus.get(999, val));
}

void test_exists() {
    TEST_ASSERT_FALSE(bus.exists(100));
    bus.define(100, "ref", SignalBus::Kind::REF, 0.0f);
    TEST_ASSERT_TRUE(bus.exists(100));
}

void test_count() {
    TEST_ASSERT_EQUAL(0, bus.count());
    bus.define(100, "a", SignalBus::Kind::REF, 0.0f);
    bus.define(101, "b", SignalBus::Kind::MEAS, 0.0f);
    TEST_ASSERT_EQUAL(2, bus.count());
}

void test_clear() {
    bus.define(100, "a", SignalBus::Kind::REF, 0.0f);
    bus.define(101, "b", SignalBus::Kind::MEAS, 0.0f);
    TEST_ASSERT_EQUAL(2, bus.count());
    bus.clear();
    TEST_ASSERT_EQUAL(0, bus.count());
}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_define_and_get);
    RUN_TEST(test_set_updates_value);
    RUN_TEST(test_get_nonexistent_returns_false);
    RUN_TEST(test_exists);
    RUN_TEST(test_count);
    RUN_TEST(test_clear);
    return UNITY_END();
}