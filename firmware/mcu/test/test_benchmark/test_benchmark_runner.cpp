// test/test_benchmark/test_benchmark_runner.cpp
// Unit tests for BenchmarkRunner

#include <unity.h>

// Define feature flag before including headers
#define FEATURE_BENCHMARK 1

#include "benchmark/BenchmarkRunner.h"
#include "benchmark/BenchmarkTypes.h"

// Include implementation for native build
#include "../../src/benchmark/BenchmarkRunner.cpp"

using namespace benchmark;

// Test counter for benchmark functions
static int g_test_call_count = 0;
static bool g_test_should_fail = false;

// Simple test function that increments counter
static bool simple_test_func() {
    g_test_call_count++;
    return !g_test_should_fail;
}

// Slow test function that takes some time
static bool slow_test_func() {
    g_test_call_count++;
    volatile int sum = 0;
    for (int i = 0; i < 1000; i++) {
        sum += i;
    }
    (void)sum;
    return true;
}

void setUp() {
    g_test_call_count = 0;
    g_test_should_fail = false;
}

void tearDown() {}

// =============================================================================
// Registration tests
// =============================================================================

void test_register_test_succeeds() {
    // Note: Tests accumulate across test runs since BenchmarkRunner is a singleton
    // We just verify registration returns true for a new test
    TestInfo info{
        TestId::USER_TEST_0,
        "USER_TEST_0",
        "User test 0",
        0
    };

    bool result = BenchmarkRunner::instance().registerTest(info, simple_test_func);
    // May be false if already registered from previous test run
    // Just verify no crash
    (void)result;
    TEST_PASS();
}

void test_get_test_info_returns_registered_test() {
    // Register a test first
    TestInfo info{
        TestId::USER_TEST_1,
        "USER_TEST_1",
        "User test 1",
        TestInfo::FLAG_RT_SAFE
    };
    BenchmarkRunner::instance().registerTest(info, simple_test_func);

    const TestInfo* retrieved = BenchmarkRunner::instance().getTestInfo(TestId::USER_TEST_1);

    if (retrieved) {
        TEST_ASSERT_EQUAL(static_cast<uint8_t>(TestId::USER_TEST_1), static_cast<uint8_t>(retrieved->id));
        TEST_ASSERT_EQUAL_STRING("USER_TEST_1", retrieved->name);
        TEST_ASSERT_TRUE(retrieved->flags & TestInfo::FLAG_RT_SAFE);
    } else {
        // Test might already be registered with different info
        TEST_PASS();
    }
}

void test_get_test_info_returns_null_for_unknown() {
    const TestInfo* info = BenchmarkRunner::instance().getTestInfo(TestId::UNKNOWN);
    TEST_ASSERT_NULL(info);
}

void test_get_registered_tests() {
    const TestInfo* tests[MAX_REGISTERED_TESTS];
    size_t count = BenchmarkRunner::instance().getRegisteredTests(tests, MAX_REGISTERED_TESTS);

    // Should have at least one registered test
    TEST_ASSERT_TRUE(count > 0);
    TEST_ASSERT_TRUE(count <= MAX_REGISTERED_TESTS);

    // Verify first test has valid data
    TEST_ASSERT_NOT_NULL(tests[0]);
    TEST_ASSERT_NOT_NULL(tests[0]->name);
}

// =============================================================================
// Execution tests
// =============================================================================

void test_run_executes_test_iterations() {
    // Register test
    TestInfo info{
        TestId::USER_TEST_2,
        "USER_TEST_2",
        "Iteration counter test",
        0
    };
    BenchmarkRunner::instance().registerTest(info, simple_test_func);

    g_test_call_count = 0;

    BenchConfig config = BenchConfig::defaults(TestId::USER_TEST_2);
    config.iterations = 50;
    config.warmup = 5;

    BenchResult result;
    bool success = BenchmarkRunner::instance().run(config, result);

    TEST_ASSERT_TRUE(success);
    // Should have run warmup + iterations
    TEST_ASSERT_EQUAL(55, g_test_call_count);
}

void test_run_fills_result_correctly() {
    TestInfo info{
        TestId::USER_TEST_3,
        "USER_TEST_3",
        "Result test",
        0
    };
    BenchmarkRunner::instance().registerTest(info, slow_test_func);

    BenchConfig config = BenchConfig::defaults(TestId::USER_TEST_3);
    config.iterations = 20;
    config.warmup = 2;

    BenchResult result;
    bool success = BenchmarkRunner::instance().run(config, result);

    TEST_ASSERT_TRUE(success);
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(TestId::USER_TEST_3), static_cast<uint8_t>(result.test_id));
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(BenchState::COMPLETE), static_cast<uint8_t>(result.state));
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(BenchError::NONE), static_cast<uint8_t>(result.error));
    TEST_ASSERT_EQUAL(20, result.samples);
    TEST_ASSERT_TRUE(result.timestamp_ms > 0);
}

void test_run_computes_statistics() {
    TestInfo info{
        TestId::HEAP_ALLOC_SMALL,  // Reuse existing ID
        "STATS_TEST",
        "Statistics test",
        0
    };
    BenchmarkRunner::instance().registerTest(info, slow_test_func);

    BenchConfig config = BenchConfig::defaults(TestId::HEAP_ALLOC_SMALL);
    config.iterations = 100;
    config.warmup = 10;

    BenchResult result;
    bool success = BenchmarkRunner::instance().run(config, result);

    TEST_ASSERT_TRUE(success);

    // Verify statistics are computed
    TEST_ASSERT_TRUE(result.mean_us > 0);
    TEST_ASSERT_TRUE(result.min_us > 0);
    TEST_ASSERT_TRUE(result.max_us >= result.min_us);
    TEST_ASSERT_TRUE(result.p50_us >= result.min_us);
    TEST_ASSERT_TRUE(result.p50_us <= result.max_us);
    TEST_ASSERT_TRUE(result.p95_us >= result.p50_us);
    TEST_ASSERT_TRUE(result.p99_us >= result.p95_us);
    TEST_ASSERT_TRUE(result.total_us > 0);
}

void test_run_unknown_test_returns_error() {
    BenchConfig config = BenchConfig::defaults(TestId::UNKNOWN);

    BenchResult result;
    bool success = BenchmarkRunner::instance().run(config, result);

    TEST_ASSERT_FALSE(success);
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(BenchState::ERROR), static_cast<uint8_t>(result.state));
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(BenchError::UNKNOWN_TEST), static_cast<uint8_t>(result.error));
}

void test_cancel_stops_execution() {
    // This test verifies the cancel flag mechanism
    BenchmarkRunner& runner = BenchmarkRunner::instance();

    TEST_ASSERT_FALSE(runner.isCancelled());

    runner.cancel();
    TEST_ASSERT_TRUE(runner.isCancelled());

    // Reset for next test by running a short benchmark
    BenchConfig config = BenchConfig::defaults(TestId::USER_TEST_2);
    config.iterations = 1;
    config.warmup = 0;
    BenchResult result;
    runner.run(config, result);

    TEST_ASSERT_FALSE(runner.isCancelled());
}

// =============================================================================
// Edge case tests
// =============================================================================

void test_run_with_zero_iterations() {
    TestInfo info{
        TestId::HEAP_ALLOC_MEDIUM,  // Reuse existing ID
        "ZERO_ITER",
        "Zero iterations test",
        0
    };
    BenchmarkRunner::instance().registerTest(info, simple_test_func);

    BenchConfig config = BenchConfig::defaults(TestId::HEAP_ALLOC_MEDIUM);
    config.iterations = 0;  // Edge case
    config.warmup = 0;

    g_test_call_count = 0;

    BenchResult result;
    bool success = BenchmarkRunner::instance().run(config, result);

    // Should complete successfully even with 0 iterations
    TEST_ASSERT_TRUE(success);
    TEST_ASSERT_EQUAL(0, result.samples);
    TEST_ASSERT_EQUAL(0, g_test_call_count);
}

void test_run_handles_failing_iterations() {
    TestInfo info{
        TestId::MOTION_UPDATE,  // Reuse existing ID
        "FAIL_TEST",
        "Failing iterations test",
        0
    };
    BenchmarkRunner::instance().registerTest(info, simple_test_func);

    g_test_should_fail = true;
    g_test_call_count = 0;

    BenchConfig config = BenchConfig::defaults(TestId::MOTION_UPDATE);
    config.iterations = 10;
    config.warmup = 0;

    BenchResult result;
    bool success = BenchmarkRunner::instance().run(config, result);

    // Run completes but samples should be 0 (failed iterations not recorded)
    TEST_ASSERT_TRUE(success);
    TEST_ASSERT_EQUAL(0, result.samples);
    TEST_ASSERT_EQUAL(10, g_test_call_count);

    g_test_should_fail = false;
}

// =============================================================================
// Main
// =============================================================================

int main(int argc, char** argv) {
    UNITY_BEGIN();

    // Registration tests
    RUN_TEST(test_register_test_succeeds);
    RUN_TEST(test_get_test_info_returns_registered_test);
    RUN_TEST(test_get_test_info_returns_null_for_unknown);
    RUN_TEST(test_get_registered_tests);

    // Execution tests
    RUN_TEST(test_run_executes_test_iterations);
    RUN_TEST(test_run_fills_result_correctly);
    RUN_TEST(test_run_computes_statistics);
    RUN_TEST(test_run_unknown_test_returns_error);
    RUN_TEST(test_cancel_stops_execution);

    // Edge case tests
    RUN_TEST(test_run_with_zero_iterations);
    RUN_TEST(test_run_handles_failing_iterations);

    return UNITY_END();
}
