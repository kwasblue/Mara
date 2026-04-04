#include <unity.h>
#include "control/SignalBus.h"

// Include implementation for native build
#include "../../src/control/SignalBus.cpp"

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

// -----------------------------------------------------------------------------
// New tests for coverage
// -----------------------------------------------------------------------------

void test_remove() {
    bus.define(100, "a", SignalBus::Kind::REF, 1.0f);
    bus.define(101, "b", SignalBus::Kind::MEAS, 2.0f);
    bus.define(102, "c", SignalBus::Kind::OUT, 3.0f);
    TEST_ASSERT_EQUAL(3, bus.count());

    // Remove middle signal
    TEST_ASSERT_TRUE(bus.remove(101));
    TEST_ASSERT_EQUAL(2, bus.count());
    TEST_ASSERT_FALSE(bus.exists(101));

    // Verify other signals still work with correct values
    float val;
    TEST_ASSERT_TRUE(bus.get(100, val));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.0f, val);
    TEST_ASSERT_TRUE(bus.get(102, val));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 3.0f, val);

    // Remove nonexistent
    TEST_ASSERT_FALSE(bus.remove(999));

    // Remove first
    TEST_ASSERT_TRUE(bus.remove(100));
    TEST_ASSERT_EQUAL(1, bus.count());

    // Remove last
    TEST_ASSERT_TRUE(bus.remove(102));
    TEST_ASSERT_EQUAL(0, bus.count());
}

void test_create_alias_and_resolve() {
    bus.define(100, "velocity", SignalBus::Kind::MEAS, 0.0f);

    // Create alias
    TEST_ASSERT_TRUE(bus.createAlias(100, "vel"));

    // resolveId works for signal name
    TEST_ASSERT_EQUAL(100, bus.resolveId("velocity"));

    // resolveId works for alias
    TEST_ASSERT_EQUAL(100, bus.resolveId("vel"));

    // resolveId returns 0 for unknown
    TEST_ASSERT_EQUAL(0, bus.resolveId("unknown"));
    TEST_ASSERT_EQUAL(0, bus.resolveId(""));
    TEST_ASSERT_EQUAL(0, bus.resolveId(nullptr));

    // Cannot create alias for nonexistent signal
    TEST_ASSERT_FALSE(bus.createAlias(999, "nope"));

    // Cannot create duplicate alias
    TEST_ASSERT_FALSE(bus.createAlias(100, "vel"));

    // Cannot create empty alias
    TEST_ASSERT_FALSE(bus.createAlias(100, ""));
    TEST_ASSERT_FALSE(bus.createAlias(100, nullptr));
}

void test_remove_alias() {
    bus.define(100, "velocity", SignalBus::Kind::MEAS, 0.0f);
    bus.createAlias(100, "vel");

    // Alias works before removal
    TEST_ASSERT_EQUAL(100, bus.resolveId("vel"));

    // Remove alias
    TEST_ASSERT_TRUE(bus.removeAlias("vel"));

    // Alias no longer resolves
    TEST_ASSERT_EQUAL(0, bus.resolveId("vel"));

    // Signal name still works
    TEST_ASSERT_EQUAL(100, bus.resolveId("velocity"));

    // Remove nonexistent alias returns false
    TEST_ASSERT_FALSE(bus.removeAlias("nope"));
    TEST_ASSERT_FALSE(bus.removeAlias(nullptr));
}

void test_get_and_set_by_name() {
    bus.define(100, "velocity", SignalBus::Kind::MEAS, 0.0f);
    bus.createAlias(100, "vel");

    // Set by signal name
    TEST_ASSERT_TRUE(bus.setByName("velocity", 5.0f, 1000));
    float val;
    TEST_ASSERT_TRUE(bus.getByName("velocity", val));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 5.0f, val);

    // Set by alias
    TEST_ASSERT_TRUE(bus.setByName("vel", 10.0f, 2000));
    TEST_ASSERT_TRUE(bus.getByName("vel", val));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 10.0f, val);

    // Both name and alias return same value
    TEST_ASSERT_TRUE(bus.getByName("velocity", val));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 10.0f, val);

    // Nonexistent name
    TEST_ASSERT_FALSE(bus.setByName("unknown", 1.0f, 0));
    TEST_ASSERT_FALSE(bus.getByName("unknown", val));
}

void test_set_with_rate_limit_min_interval() {
    bus.define(100, "sig", SignalBus::Kind::REF, 0.0f);

    // Set 10ms minimum interval
    bus.setGlobalRateLimit(10, 0);
    TEST_ASSERT_EQUAL(10, bus.getMinInterval());
    TEST_ASSERT_EQUAL(0, bus.getMaxUpdatesPerSec());

    // First set succeeds
    auto result = bus.setWithRateLimit(100, 1.0f, 1000);
    TEST_ASSERT_EQUAL(SignalBus::SetResult::OK, result);

    // Too soon - rate limited
    result = bus.setWithRateLimit(100, 2.0f, 1005);
    TEST_ASSERT_EQUAL(SignalBus::SetResult::RATE_LIMITED_TIME, result);

    // Value unchanged
    float val;
    bus.get(100, val);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.0f, val);

    // After interval - succeeds
    result = bus.setWithRateLimit(100, 3.0f, 1010);
    TEST_ASSERT_EQUAL(SignalBus::SetResult::OK, result);
    bus.get(100, val);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 3.0f, val);

    // Nonexistent signal
    result = bus.setWithRateLimit(999, 1.0f, 1000);
    TEST_ASSERT_EQUAL(SignalBus::SetResult::SIGNAL_NOT_FOUND, result);
}

void test_set_with_rate_limit_max_updates() {
    bus.define(100, "sig", SignalBus::Kind::REF, 0.0f);

    // Set max 3 updates per second
    bus.setGlobalRateLimit(0, 3);
    TEST_ASSERT_EQUAL(0, bus.getMinInterval());
    TEST_ASSERT_EQUAL(3, bus.getMaxUpdatesPerSec());

    // First 3 updates in same second succeed
    TEST_ASSERT_EQUAL(SignalBus::SetResult::OK, bus.setWithRateLimit(100, 1.0f, 1000));
    TEST_ASSERT_EQUAL(SignalBus::SetResult::OK, bus.setWithRateLimit(100, 2.0f, 1100));
    TEST_ASSERT_EQUAL(SignalBus::SetResult::OK, bus.setWithRateLimit(100, 3.0f, 1200));

    // 4th update in same window fails
    TEST_ASSERT_EQUAL(SignalBus::SetResult::RATE_LIMITED_COUNT,
                      bus.setWithRateLimit(100, 4.0f, 1300));

    // Value is still 3.0
    float val;
    bus.get(100, val);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 3.0f, val);

    // After 1 second window resets, updates succeed again
    TEST_ASSERT_EQUAL(SignalBus::SetResult::OK, bus.setWithRateLimit(100, 5.0f, 2000));
    bus.get(100, val);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 5.0f, val);
}

void test_snapshot() {
    bus.define(100, "a", SignalBus::Kind::REF, 1.0f);
    bus.define(101, "b", SignalBus::Kind::MEAS, 2.0f);
    bus.define(102, "c", SignalBus::Kind::OUT, 3.0f);

    // Set timestamps
    bus.set(100, 1.0f, 1000);
    bus.set(101, 2.0f, 2000);
    bus.set(102, 3.0f, 3000);

    // Take full snapshot
    SignalBus::SignalSnapshot snaps[3];
    size_t count = bus.snapshot(snaps, 3);
    TEST_ASSERT_EQUAL(3, count);

    // Verify contents (order matches define order)
    TEST_ASSERT_EQUAL(100, snaps[0].id);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.0f, snaps[0].value);
    TEST_ASSERT_EQUAL(1000, snaps[0].ts_ms);
    TEST_ASSERT_EQUAL(SignalBus::Kind::REF, snaps[0].kind);

    TEST_ASSERT_EQUAL(101, snaps[1].id);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 2.0f, snaps[1].value);
    TEST_ASSERT_EQUAL(2000, snaps[1].ts_ms);
    TEST_ASSERT_EQUAL(SignalBus::Kind::MEAS, snaps[1].kind);

    TEST_ASSERT_EQUAL(102, snaps[2].id);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 3.0f, snaps[2].value);
    TEST_ASSERT_EQUAL(3000, snaps[2].ts_ms);
    TEST_ASSERT_EQUAL(SignalBus::Kind::OUT, snaps[2].kind);

    // Partial snapshot (max_count < actual)
    SignalBus::SignalSnapshot snaps2[2];
    count = bus.snapshot(snaps2, 2);
    TEST_ASSERT_EQUAL(2, count);
    TEST_ASSERT_EQUAL(100, snaps2[0].id);
    TEST_ASSERT_EQUAL(101, snaps2[1].id);

    // Invalid parameters
    count = bus.snapshot(nullptr, 3);
    TEST_ASSERT_EQUAL(0, count);
    count = bus.snapshot(snaps, 0);
    TEST_ASSERT_EQUAL(0, count);
}

void test_capacity_limit() {
    // Define signals up to capacity
    // Note: MAX_SIGNALS is 128, but we test a smaller subset to keep test fast
    for (uint16_t i = 0; i < 10; i++) {
        TEST_ASSERT_TRUE(bus.define(i, "sig", SignalBus::Kind::REF, 0.0f));
    }
    TEST_ASSERT_EQUAL(10, bus.count());

    // Verify all signals accessible
    for (uint16_t i = 0; i < 10; i++) {
        TEST_ASSERT_TRUE(bus.exists(i));
    }
}

void test_define_same_id_updates() {
    // First define
    TEST_ASSERT_TRUE(bus.define(100, "first", SignalBus::Kind::REF, 1.0f));
    TEST_ASSERT_EQUAL(1, bus.count());

    float val;
    bus.get(100, val);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.0f, val);

    // Define same ID again - updates existing (idempotent)
    TEST_ASSERT_TRUE(bus.define(100, "updated", SignalBus::Kind::MEAS, 5.0f));
    TEST_ASSERT_EQUAL(1, bus.count());  // Count unchanged

    // Value and kind updated
    bus.get(100, val);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 5.0f, val);

    const auto* sig = bus.find(100);
    TEST_ASSERT_NOT_NULL(sig);
    TEST_ASSERT_EQUAL(SignalBus::Kind::MEAS, sig->kind);
}

void test_find() {
    bus.define(100, "velocity", SignalBus::Kind::MEAS, 42.0f);

    const auto* sig = bus.find(100);
    TEST_ASSERT_NOT_NULL(sig);
    TEST_ASSERT_EQUAL(100, sig->id);
    TEST_ASSERT_EQUAL_STRING("velocity", sig->name);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 42.0f, sig->value);

    // Nonexistent
    TEST_ASSERT_NULL(bus.find(999));
}

void test_get_timestamp() {
    bus.define(100, "sig", SignalBus::Kind::REF, 0.0f);
    bus.set(100, 1.0f, 12345);

    uint32_t ts;
    TEST_ASSERT_TRUE(bus.getTimestamp(100, ts));
    TEST_ASSERT_EQUAL(12345, ts);

    // Nonexistent
    TEST_ASSERT_FALSE(bus.getTimestamp(999, ts));
}

// -----------------------------------------------------------------------------
// Phase 12: Signal Namespace and Auto-Signals Tests
// -----------------------------------------------------------------------------

void test_signal_namespace_constants() {
    // User signal range
    TEST_ASSERT_EQUAL(1, SignalNamespace::USER_MIN);
    TEST_ASSERT_EQUAL(999, SignalNamespace::USER_MAX);

    // Auto-signal range
    TEST_ASSERT_EQUAL(1000, SignalNamespace::AUTO_MIN);
    TEST_ASSERT_EQUAL(1999, SignalNamespace::AUTO_MAX);

    // IMU signals
    TEST_ASSERT_EQUAL(1000, SignalNamespace::IMU_AX);
    TEST_ASSERT_EQUAL(1001, SignalNamespace::IMU_AY);
    TEST_ASSERT_EQUAL(1002, SignalNamespace::IMU_AZ);
    TEST_ASSERT_EQUAL(1003, SignalNamespace::IMU_GX);
    TEST_ASSERT_EQUAL(1004, SignalNamespace::IMU_GY);
    TEST_ASSERT_EQUAL(1005, SignalNamespace::IMU_GZ);
    TEST_ASSERT_EQUAL(1006, SignalNamespace::IMU_PITCH);
    TEST_ASSERT_EQUAL(1007, SignalNamespace::IMU_ROLL);

    // Encoder base
    TEST_ASSERT_EQUAL(1020, SignalNamespace::ENCODER_BASE);

    // Motor/servo bases
    TEST_ASSERT_EQUAL(1040, SignalNamespace::DC_MOTOR_BASE);
    TEST_ASSERT_EQUAL(1060, SignalNamespace::SERVO_BASE);
    TEST_ASSERT_EQUAL(1080, SignalNamespace::ULTRASONIC_BASE);
}

void test_signal_namespace_helpers() {
    // isAutoSignal
    TEST_ASSERT_FALSE(SignalNamespace::isAutoSignal(0));
    TEST_ASSERT_FALSE(SignalNamespace::isAutoSignal(100));
    TEST_ASSERT_FALSE(SignalNamespace::isAutoSignal(999));
    TEST_ASSERT_TRUE(SignalNamespace::isAutoSignal(1000));
    TEST_ASSERT_TRUE(SignalNamespace::isAutoSignal(1500));
    TEST_ASSERT_TRUE(SignalNamespace::isAutoSignal(1999));
    TEST_ASSERT_FALSE(SignalNamespace::isAutoSignal(2000));

    // isUserSignal
    TEST_ASSERT_FALSE(SignalNamespace::isUserSignal(0));
    TEST_ASSERT_TRUE(SignalNamespace::isUserSignal(1));
    TEST_ASSERT_TRUE(SignalNamespace::isUserSignal(500));
    TEST_ASSERT_TRUE(SignalNamespace::isUserSignal(999));
    TEST_ASSERT_FALSE(SignalNamespace::isUserSignal(1000));
}

void test_define_auto_signal() {
    // defineAutoSignal should succeed for auto-signal range
    TEST_ASSERT_TRUE(bus.defineAutoSignal(
        SignalNamespace::IMU_AX, "imu.ax", SignalBus::Kind::MEAS, 0.0f));

    // Verify signal exists
    TEST_ASSERT_TRUE(bus.exists(SignalNamespace::IMU_AX));

    // Verify read_only flag is set (cannot use regular set)
    TEST_ASSERT_FALSE(bus.set(SignalNamespace::IMU_AX, 9.81f, 1000));

    // Value should still be initial (0.0)
    float val;
    bus.get(SignalNamespace::IMU_AX, val);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, val);
}

void test_set_auto_signal_bypasses_read_only() {
    bus.defineAutoSignal(SignalNamespace::IMU_AY, "imu.ay", SignalBus::Kind::MEAS, 0.0f);

    // setAutoSignal should bypass read_only protection
    TEST_ASSERT_TRUE(bus.setAutoSignal(SignalNamespace::IMU_AY, 9.81f, 1000));

    // Verify value was set
    float val;
    bus.get(SignalNamespace::IMU_AY, val);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 9.81f, val);
}

void test_define_user_signal_in_auto_range_fails() {
    // Regular define() should fail for auto-signal range IDs
    TEST_ASSERT_FALSE(bus.define(
        SignalNamespace::IMU_AZ, "user_imu", SignalBus::Kind::MEAS, 0.0f));

    // Signal should not exist
    TEST_ASSERT_FALSE(bus.exists(SignalNamespace::IMU_AZ));
}

void test_define_auto_signal_in_user_range_fails() {
    // defineAutoSignal() should fail for user-signal range IDs
    TEST_ASSERT_FALSE(bus.defineAutoSignal(
        100, "user_signal", SignalBus::Kind::MEAS, 0.0f));

    // Signal should not exist
    TEST_ASSERT_FALSE(bus.exists(100));
}

void test_read_only_signal_via_set_by_name() {
    bus.defineAutoSignal(SignalNamespace::IMU_GX, "imu.gx", SignalBus::Kind::MEAS, 0.0f);

    // setByName should also fail for read_only signals
    TEST_ASSERT_FALSE(bus.setByName("imu.gx", 100.0f, 1000));

    // Value unchanged
    float val;
    bus.get(SignalNamespace::IMU_GX, val);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, val);
}

// -----------------------------------------------------------------------------
// Phase 13: Signal Trace Subscription Tests
// -----------------------------------------------------------------------------

void test_set_trace_signals() {
    bus.define(100, "a", SignalBus::Kind::REF, 1.0f);
    bus.define(101, "b", SignalBus::Kind::MEAS, 2.0f);
    bus.define(102, "c", SignalBus::Kind::OUT, 3.0f);

    // Initially no trace
    TEST_ASSERT_FALSE(bus.isTraceEnabled());

    // Set trace signals
    uint16_t ids[] = {100, 102};  // Skip 101
    bus.setTraceSignals(ids, 2, 20);

    // Trace should be enabled
    TEST_ASSERT_TRUE(bus.isTraceEnabled());
    TEST_ASSERT_EQUAL(20, bus.getTraceRateHz());
}

void test_get_traced_signals() {
    bus.define(100, "a", SignalBus::Kind::REF, 1.0f);
    bus.define(101, "b", SignalBus::Kind::MEAS, 2.0f);

    uint16_t ids[] = {100, 101};
    bus.setTraceSignals(ids, 2, 10);

    // Get traced signal IDs
    uint16_t outIds[16];
    size_t count = bus.getTracedSignals(outIds, 16);

    TEST_ASSERT_EQUAL(2, count);
    TEST_ASSERT_EQUAL(100, outIds[0]);
    TEST_ASSERT_EQUAL(101, outIds[1]);
}

void test_get_traced_snapshot() {
    bus.define(100, "a", SignalBus::Kind::REF, 1.0f);
    bus.define(101, "b", SignalBus::Kind::MEAS, 2.0f);
    bus.define(102, "c", SignalBus::Kind::OUT, 3.0f);

    // Set timestamps
    bus.set(100, 1.0f, 1000);
    bus.set(101, 2.0f, 2000);
    bus.set(102, 3.0f, 3000);

    // Trace only 100 and 102
    uint16_t ids[] = {100, 102};
    bus.setTraceSignals(ids, 2);

    // Get traced snapshot
    SignalBus::SignalSnapshot snaps[16];
    size_t count = bus.getTracedSnapshot(snaps, 16);

    TEST_ASSERT_EQUAL(2, count);

    // Should only contain traced signals
    TEST_ASSERT_EQUAL(100, snaps[0].id);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.0f, snaps[0].value);
    TEST_ASSERT_EQUAL(1000, snaps[0].ts_ms);

    TEST_ASSERT_EQUAL(102, snaps[1].id);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 3.0f, snaps[1].value);
    TEST_ASSERT_EQUAL(3000, snaps[1].ts_ms);
}

void test_traced_snapshot_empty_when_disabled() {
    bus.define(100, "a", SignalBus::Kind::REF, 1.0f);

    // No trace set
    TEST_ASSERT_FALSE(bus.isTraceEnabled());

    SignalBus::SignalSnapshot snaps[16];
    size_t count = bus.getTracedSnapshot(snaps, 16);

    TEST_ASSERT_EQUAL(0, count);
}

void test_clear_trace_signals() {
    bus.define(100, "a", SignalBus::Kind::REF, 1.0f);

    uint16_t ids[] = {100};
    bus.setTraceSignals(ids, 1);
    TEST_ASSERT_TRUE(bus.isTraceEnabled());

    // Clear trace by passing empty
    bus.setTraceSignals(nullptr, 0);
    TEST_ASSERT_FALSE(bus.isTraceEnabled());
}

void test_trace_max_signals_limit() {
    // Define more signals than MAX_TRACE_SIGNALS (16)
    for (uint16_t i = 0; i < 20; i++) {
        bus.define(i + 1, "sig", SignalBus::Kind::REF, static_cast<float>(i));
    }

    // Try to trace 20 signals
    uint16_t ids[20];
    for (uint16_t i = 0; i < 20; i++) {
        ids[i] = i + 1;
    }
    bus.setTraceSignals(ids, 20);

    // Should only trace up to MAX_TRACE_SIGNALS (16)
    uint16_t outIds[20];
    size_t count = bus.getTracedSignals(outIds, 20);
    TEST_ASSERT_EQUAL(16, count);  // Capped at MAX_TRACE_SIGNALS
}

void test_trace_nonexistent_signal_ignored() {
    bus.define(100, "a", SignalBus::Kind::REF, 1.0f);

    // Include nonexistent signal 999
    uint16_t ids[] = {100, 999};
    bus.setTraceSignals(ids, 2);

    // Snapshot should only include existing signals
    SignalBus::SignalSnapshot snaps[16];
    size_t count = bus.getTracedSnapshot(snaps, 16);

    TEST_ASSERT_EQUAL(1, count);  // Only signal 100
    TEST_ASSERT_EQUAL(100, snaps[0].id);
}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_define_and_get);
    RUN_TEST(test_set_updates_value);
    RUN_TEST(test_get_nonexistent_returns_false);
    RUN_TEST(test_exists);
    RUN_TEST(test_count);
    RUN_TEST(test_clear);
    RUN_TEST(test_remove);
    RUN_TEST(test_create_alias_and_resolve);
    RUN_TEST(test_remove_alias);
    RUN_TEST(test_get_and_set_by_name);
    RUN_TEST(test_set_with_rate_limit_min_interval);
    RUN_TEST(test_set_with_rate_limit_max_updates);
    RUN_TEST(test_snapshot);
    RUN_TEST(test_capacity_limit);
    RUN_TEST(test_define_same_id_updates);
    RUN_TEST(test_find);
    RUN_TEST(test_get_timestamp);
    // Phase 12: Signal Namespace and Auto-Signals
    RUN_TEST(test_signal_namespace_constants);
    RUN_TEST(test_signal_namespace_helpers);
    RUN_TEST(test_define_auto_signal);
    RUN_TEST(test_set_auto_signal_bypasses_read_only);
    RUN_TEST(test_define_user_signal_in_auto_range_fails);
    RUN_TEST(test_define_auto_signal_in_user_range_fails);
    RUN_TEST(test_read_only_signal_via_set_by_name);
    // Phase 13: Signal Trace Subscription
    RUN_TEST(test_set_trace_signals);
    RUN_TEST(test_get_traced_signals);
    RUN_TEST(test_get_traced_snapshot);
    RUN_TEST(test_traced_snapshot_empty_when_disabled);
    RUN_TEST(test_clear_trace_signals);
    RUN_TEST(test_trace_max_signals_limit);
    RUN_TEST(test_trace_nonexistent_signal_ignored);
    return UNITY_END();
}
