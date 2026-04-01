// include/benchmark/BenchmarkRunner.h
// RT-safe benchmark execution engine

#pragma once

#ifdef FEATURE_BENCHMARK

#include <cstdint>
#include <array>
#include <functional>
#include "benchmark/BenchmarkTypes.h"

namespace benchmark {

/**
 * Function signature for benchmark tests.
 * The function should execute one iteration of the test.
 * Returns true if iteration succeeded, false if it should be skipped.
 */
using TestFunc = std::function<bool()>;

/**
 * Registered test entry.
 */
struct RegisteredTest {
    TestInfo info;
    TestFunc func;
    bool     registered;
};

/**
 * BenchmarkRunner - Executes benchmarks and computes statistics.
 *
 * Key features:
 * - Static test registration (no heap allocation in RT context)
 * - Fixed-size sample buffer (std::array<uint32_t, 256>)
 * - Percentile calculation using quickselect
 * - RT_SAFE execution for control-task tests
 *
 * Usage:
 *   // At startup
 *   BenchmarkRunner::instance().registerTest(TestInfo{...}, []() {
 *       // Test code
 *       return true;
 *   });
 *
 *   // Later
 *   BenchConfig cfg = BenchConfig::defaults(TestId::PID_STEP);
 *   BenchResult result;
 *   runner.run(cfg, result);
 */
class BenchmarkRunner {
public:
    // Singleton access
    static BenchmarkRunner& instance();

    /**
     * Register a test at startup.
     * Must be called before any tests are run.
     * Returns false if registration fails (e.g., table full).
     */
    bool registerTest(const TestInfo& info, TestFunc func);

    /**
     * Get information about a registered test.
     * Returns nullptr if test not found.
     */
    const TestInfo* getTestInfo(TestId id) const;

    /**
     * Get all registered tests.
     */
    size_t getRegisteredTests(const TestInfo** out, size_t max_count) const;

    /**
     * Run a benchmark synchronously.
     * Fills in result with timing statistics.
     * Returns true if benchmark completed successfully.
     */
    bool run(const BenchConfig& config, BenchResult& result);

    /**
     * Cancel any running benchmark.
     * Sets cancelled_ flag which tests should check.
     */
    void cancel();

    /**
     * Check if a cancel was requested.
     */
    bool isCancelled() const { return cancelled_; }

    /**
     * Get count of registered tests.
     */
    size_t registeredCount() const { return registeredCount_; }

private:
    BenchmarkRunner() = default;
    ~BenchmarkRunner() = default;

    // Non-copyable
    BenchmarkRunner(const BenchmarkRunner&) = delete;
    BenchmarkRunner& operator=(const BenchmarkRunner&) = delete;

    // Find a registered test
    const RegisteredTest* findTest(TestId id) const;
    RegisteredTest* findTest(TestId id);

    // Statistics helpers
    void computeStats(BenchResult& result);
    uint32_t quickSelect(size_t k);  // Find k-th smallest element

    // Test registry (static allocation)
    std::array<RegisteredTest, MAX_REGISTERED_TESTS> tests_{};
    size_t registeredCount_ = 0;

    // Sample buffer for current test (static allocation)
    std::array<uint32_t, MAX_SAMPLE_COUNT> samples_{};
    size_t sampleCount_ = 0;

    // State
    volatile bool cancelled_ = false;
    bool running_ = false;
};

/**
 * RAII helper for registering tests at static init time.
 *
 * Usage:
 *   static BenchmarkRegistrar reg_pid_step{
 *       TestInfo{TestId::PID_STEP, "PID_STEP", "PID controller step()", TestInfo::FLAG_RT_SAFE},
 *       []() { pidController.step(); return true; }
 *   };
 */
class BenchmarkRegistrar {
public:
    BenchmarkRegistrar(const TestInfo& info, TestFunc func) {
        BenchmarkRunner::instance().registerTest(info, func);
    }
};

}  // namespace benchmark

#endif  // FEATURE_BENCHMARK
