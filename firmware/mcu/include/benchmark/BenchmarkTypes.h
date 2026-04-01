// include/benchmark/BenchmarkTypes.h
// Core types for the benchmarking subsystem
// Guarded by FEATURE_BENCHMARK to save flash/RAM when not needed

#pragma once

#ifdef FEATURE_BENCHMARK

#include <cstdint>
#include <array>

namespace benchmark {

/**
 * Test identifiers for built-in benchmarks.
 * Each test measures a specific subsystem or operation.
 */
enum class TestId : uint8_t {
    // Core timing tests (0x01-0x0F)
    LOOP_TIMING          = 0x01,  // Control loop iteration time
    SIGNAL_BUS_LATENCY   = 0x02,  // SignalBus get/set time
    INTENT_CONSUME       = 0x03,  // IntentBuffer consume time
    EVENT_BUS_PUBLISH    = 0x04,  // EventBus publish latency

    // Command/comms tests (0x20-0x2F)
    PING_INTERNAL        = 0x20,  // Internal ping processing
    CMD_DECODE           = 0x21,  // JSON command decode time
    TELEM_ENCODE         = 0x22,  // Binary telemetry encode
    TELEM_JSON_ENCODE    = 0x23,  // JSON telemetry encode

    // Control subsystem tests (0x30-0x3F)
    PID_STEP             = 0x30,  // PID controller step()
    OBSERVER_UPDATE      = 0x31,  // Observer update()
    KERNEL_STEP          = 0x32,  // Full ControlKernel step
    MOTION_UPDATE        = 0x33,  // MotionController update

    // Memory/allocation tests (0x40-0x4F)
    HEAP_ALLOC_SMALL     = 0x40,  // Small heap allocation (64 bytes)
    HEAP_ALLOC_MEDIUM    = 0x41,  // Medium heap allocation (512 bytes)

    // Custom/user tests (0x80-0xFF)
    USER_TEST_0          = 0x80,
    USER_TEST_1          = 0x81,
    USER_TEST_2          = 0x82,
    USER_TEST_3          = 0x83,

    UNKNOWN              = 0xFF
};

/**
 * Current state of the benchmark system.
 */
enum class BenchState : uint8_t {
    IDLE       = 0,  // No benchmark running
    RUNNING    = 1,  // Currently executing a test
    COMPLETE   = 2,  // Test finished, results available
    ERROR      = 3,  // Test failed or was cancelled
    QUEUED     = 4   // Tests queued, waiting to run
};

/**
 * Error codes for benchmark operations.
 */
enum class BenchError : uint8_t {
    NONE               = 0,
    UNKNOWN_TEST       = 1,
    QUEUE_FULL         = 2,
    TIMEOUT            = 3,
    BUDGET_EXCEEDED    = 4,
    RT_VIOLATION       = 5,
    CANCELLED          = 6,
    NOT_AVAILABLE      = 7   // Test not compiled in
};

/**
 * Configuration for a benchmark run.
 * Packed for efficient transmission.
 */
#pragma pack(push, 1)
struct BenchConfig {
    TestId   test_id;         // Which test to run
    uint16_t iterations;      // Number of iterations (1-65535)
    uint16_t warmup;          // Warmup iterations (discarded)
    uint32_t budget_us;       // Max time per iteration in microseconds (0 = no limit)
    uint8_t  flags;           // Bit flags for options

    // Flag definitions
    static constexpr uint8_t FLAG_RT_SAFE     = 0x01;  // Run in RT context
    static constexpr uint8_t FLAG_DISABLE_GC  = 0x02;  // Disable GC during test
    static constexpr uint8_t FLAG_STREAM      = 0x04;  // Stream results as they come

    // Default config
    static BenchConfig defaults(TestId id) {
        return BenchConfig{
            .test_id = id,
            .iterations = 100,
            .warmup = 10,
            .budget_us = 0,
            .flags = 0
        };
    }
};
#pragma pack(pop)
static_assert(sizeof(BenchConfig) == 10, "BenchConfig should be 10 bytes");

/**
 * Result of a benchmark run.
 * Fixed size (56 bytes) for predictable telemetry encoding.
 */
#pragma pack(push, 1)
struct BenchResult {
    // Header (8 bytes)
    TestId     test_id;       // Which test was run
    BenchState state;         // Final state
    BenchError error;         // Error code if state == ERROR
    uint8_t    reserved;      // Padding for alignment
    uint32_t   timestamp_ms;  // When test completed (millis())

    // Timing stats in microseconds (36 bytes)
    uint32_t   mean_us;       // Mean iteration time
    uint32_t   min_us;        // Minimum iteration time
    uint32_t   max_us;        // Maximum iteration time
    uint32_t   p50_us;        // 50th percentile (median)
    uint32_t   p95_us;        // 95th percentile
    uint32_t   p99_us;        // 99th percentile
    uint32_t   jitter_us;     // Standard deviation
    uint32_t   total_us;      // Total test time
    uint16_t   samples;       // Actual samples taken
    uint16_t   budget_violations;  // Iterations that exceeded budget

    // Reserved for future use (12 bytes)
    uint32_t   extra1;        // Could be throughput_hz * 100
    uint32_t   extra2;        // Could be memory delta
    uint32_t   extra3;        // Reserved

    // Initialize to defaults
    void clear() {
        test_id = TestId::UNKNOWN;
        state = BenchState::IDLE;
        error = BenchError::NONE;
        reserved = 0;
        timestamp_ms = 0;
        mean_us = 0;
        min_us = 0;
        max_us = 0;
        p50_us = 0;
        p95_us = 0;
        p99_us = 0;
        jitter_us = 0;
        total_us = 0;
        samples = 0;
        budget_violations = 0;
        extra1 = 0;
        extra2 = 0;
        extra3 = 0;
    }
};
#pragma pack(pop)
static_assert(sizeof(BenchResult) == 56, "BenchResult must be exactly 56 bytes");

/**
 * Information about a registered test.
 */
struct TestInfo {
    TestId      id;
    const char* name;        // Human-readable name (ROM string)
    const char* description; // Brief description (ROM string)
    uint8_t     flags;       // Test capabilities

    // Flag definitions
    static constexpr uint8_t FLAG_RT_SAFE    = 0x01;  // Can run in RT context
    static constexpr uint8_t FLAG_BOOT_TEST  = 0x02;  // Runs at boot
    static constexpr uint8_t FLAG_SLOW       = 0x04;  // May take > 100ms
};

// Constants
constexpr size_t MAX_SAMPLE_COUNT = 256;    // Max samples per test
constexpr size_t RESULT_HISTORY_SIZE = 8;   // Ring buffer size for results
constexpr size_t MAX_QUEUE_DEPTH = 4;       // Max queued benchmarks
constexpr size_t MAX_REGISTERED_TESTS = 32; // Max test registrations

}  // namespace benchmark

#endif  // FEATURE_BENCHMARK
