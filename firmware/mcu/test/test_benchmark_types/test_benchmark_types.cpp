// test/test_benchmark/test_benchmark_types.cpp
// Unit tests for BenchmarkTypes.h

#include <unity.h>

// Define feature flag before including headers
#define FEATURE_BENCHMARK 1

#include "benchmark/BenchmarkTypes.h"

using namespace benchmark;

void setUp() {}
void tearDown() {}

// =============================================================================
// BenchResult struct tests
// =============================================================================

void test_bench_result_size_is_56_bytes() {
    TEST_ASSERT_EQUAL(56, sizeof(BenchResult));
}

void test_bench_result_clear_resets_all_fields() {
    BenchResult result;
    result.test_id = TestId::PID_STEP;
    result.state = BenchState::COMPLETE;
    result.error = BenchError::TIMEOUT;
    result.mean_us = 1000;
    result.samples = 100;

    result.clear();

    TEST_ASSERT_EQUAL(static_cast<uint8_t>(TestId::UNKNOWN), static_cast<uint8_t>(result.test_id));
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(BenchState::IDLE), static_cast<uint8_t>(result.state));
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(BenchError::NONE), static_cast<uint8_t>(result.error));
    TEST_ASSERT_EQUAL(0, result.mean_us);
    TEST_ASSERT_EQUAL(0, result.samples);
    TEST_ASSERT_EQUAL(0, result.timestamp_ms);
}

// =============================================================================
// BenchConfig struct tests
// =============================================================================

void test_bench_config_size_is_10_bytes() {
    TEST_ASSERT_EQUAL(10, sizeof(BenchConfig));
}

void test_bench_config_defaults() {
    BenchConfig config = BenchConfig::defaults(TestId::LOOP_TIMING);

    TEST_ASSERT_EQUAL(static_cast<uint8_t>(TestId::LOOP_TIMING), static_cast<uint8_t>(config.test_id));
    TEST_ASSERT_EQUAL(100, config.iterations);
    TEST_ASSERT_EQUAL(10, config.warmup);
    TEST_ASSERT_EQUAL(0, config.budget_us);
    TEST_ASSERT_EQUAL(0, config.flags);
}

void test_bench_config_flags() {
    BenchConfig config = BenchConfig::defaults(TestId::PID_STEP);
    config.flags = BenchConfig::FLAG_RT_SAFE | BenchConfig::FLAG_DISABLE_GC;

    TEST_ASSERT_TRUE(config.flags & BenchConfig::FLAG_RT_SAFE);
    TEST_ASSERT_TRUE(config.flags & BenchConfig::FLAG_DISABLE_GC);
    TEST_ASSERT_FALSE(config.flags & BenchConfig::FLAG_STREAM);
}

// =============================================================================
// TestInfo struct tests
// =============================================================================

void test_test_info_flags() {
    TestInfo info{
        TestId::LOOP_TIMING,
        "LOOP_TIMING",
        "Test description",
        TestInfo::FLAG_RT_SAFE | TestInfo::FLAG_BOOT_TEST
    };

    TEST_ASSERT_TRUE(info.flags & TestInfo::FLAG_RT_SAFE);
    TEST_ASSERT_TRUE(info.flags & TestInfo::FLAG_BOOT_TEST);
    TEST_ASSERT_FALSE(info.flags & TestInfo::FLAG_SLOW);
}

// =============================================================================
// Enum tests
// =============================================================================

void test_test_id_values() {
    TEST_ASSERT_EQUAL(0x01, static_cast<uint8_t>(TestId::LOOP_TIMING));
    TEST_ASSERT_EQUAL(0x02, static_cast<uint8_t>(TestId::SIGNAL_BUS_LATENCY));
    TEST_ASSERT_EQUAL(0x20, static_cast<uint8_t>(TestId::PING_INTERNAL));
    TEST_ASSERT_EQUAL(0x30, static_cast<uint8_t>(TestId::PID_STEP));
    TEST_ASSERT_EQUAL(0xFF, static_cast<uint8_t>(TestId::UNKNOWN));
}

void test_bench_state_values() {
    TEST_ASSERT_EQUAL(0, static_cast<uint8_t>(BenchState::IDLE));
    TEST_ASSERT_EQUAL(1, static_cast<uint8_t>(BenchState::RUNNING));
    TEST_ASSERT_EQUAL(2, static_cast<uint8_t>(BenchState::COMPLETE));
    TEST_ASSERT_EQUAL(3, static_cast<uint8_t>(BenchState::ERROR));
    TEST_ASSERT_EQUAL(4, static_cast<uint8_t>(BenchState::QUEUED));
}

void test_bench_error_values() {
    TEST_ASSERT_EQUAL(0, static_cast<uint8_t>(BenchError::NONE));
    TEST_ASSERT_EQUAL(1, static_cast<uint8_t>(BenchError::UNKNOWN_TEST));
    TEST_ASSERT_EQUAL(6, static_cast<uint8_t>(BenchError::CANCELLED));
}

// =============================================================================
// Constants tests
// =============================================================================

void test_constants() {
    TEST_ASSERT_EQUAL(256, MAX_SAMPLE_COUNT);
    TEST_ASSERT_EQUAL(8, RESULT_HISTORY_SIZE);
    TEST_ASSERT_EQUAL(4, MAX_QUEUE_DEPTH);
    TEST_ASSERT_EQUAL(32, MAX_REGISTERED_TESTS);
}

// =============================================================================
// Main
// =============================================================================

int main(int argc, char** argv) {
    UNITY_BEGIN();

    // BenchResult tests
    RUN_TEST(test_bench_result_size_is_56_bytes);
    RUN_TEST(test_bench_result_clear_resets_all_fields);

    // BenchConfig tests
    RUN_TEST(test_bench_config_size_is_10_bytes);
    RUN_TEST(test_bench_config_defaults);
    RUN_TEST(test_bench_config_flags);

    // TestInfo tests
    RUN_TEST(test_test_info_flags);

    // Enum tests
    RUN_TEST(test_test_id_values);
    RUN_TEST(test_bench_state_values);
    RUN_TEST(test_bench_error_values);

    // Constants tests
    RUN_TEST(test_constants);

    return UNITY_END();
}
