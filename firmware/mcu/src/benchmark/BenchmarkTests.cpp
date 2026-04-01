// src/benchmark/BenchmarkTests.cpp
// Built-in benchmark test implementations

#ifdef FEATURE_BENCHMARK

#include "benchmark/BenchmarkRunner.h"
#include "benchmark/BenchmarkTypes.h"
#include "config/FeatureFlags.h"
#include <Arduino.h>

// Optional subsystem includes (no external dependencies)
#if HAS_SIGNAL_BUS
#include "control/SignalBus.h"
#endif

// ControlKernel and Observer tests disabled - require complex setup
// #if HAS_CONTROL_KERNEL
// #include "control/ControlKernel.h"
// #endif
// #if HAS_OBSERVER
// #include "control/Observer.h"
// #endif

namespace benchmark {

// ---------------------------------------------------------------------------
// Test: LOOP_TIMING (0x01)
// Measures overhead of an empty loop iteration
// ---------------------------------------------------------------------------
static bool test_loop_timing() {
    // Minimal work to measure loop overhead
    volatile uint32_t dummy = micros();
    (void)dummy;
    return true;
}

static BenchmarkRegistrar reg_loop_timing{
    TestInfo{
        TestId::LOOP_TIMING,
        "LOOP_TIMING",
        "Empty loop iteration overhead",
        TestInfo::FLAG_RT_SAFE | TestInfo::FLAG_BOOT_TEST
    },
    test_loop_timing
};

// ---------------------------------------------------------------------------
// Test: SIGNAL_BUS_LATENCY (0x02)
// Measures SignalBus get/set round-trip time
// NOTE: Uses local SignalBus instance to avoid external dependency
// ---------------------------------------------------------------------------
#if HAS_SIGNAL_BUS
static SignalBus bench_signal_bus;  // Local instance for benchmarking
static uint16_t bench_signal_id = 9999;
static bool bench_signal_defined = false;

static bool test_signal_bus_latency() {
    // Define test signal on first run
    if (!bench_signal_defined) {
        bench_signal_bus.define(bench_signal_id, "_bench_test", SignalBus::Kind::MEAS, 0.0f);
        bench_signal_defined = true;
    }

    // Set and get
    float value = static_cast<float>(micros() % 1000);
    bench_signal_bus.set(bench_signal_id, value, millis());

    float out = 0.0f;
    bench_signal_bus.get(bench_signal_id, out);

    return (out == value);
}

static BenchmarkRegistrar reg_signal_bus{
    TestInfo{
        TestId::SIGNAL_BUS_LATENCY,
        "SIGNAL_BUS",
        "SignalBus get/set latency",
        TestInfo::FLAG_RT_SAFE | TestInfo::FLAG_BOOT_TEST
    },
    test_signal_bus_latency
};
#endif  // HAS_SIGNAL_BUS

// ---------------------------------------------------------------------------
// Test: EVENT_BUS_PUBLISH (0x04)
// Measures EventBus publish latency
// ---------------------------------------------------------------------------
// Note: This would need EventBus dependency, skipped for minimal implementation

// ---------------------------------------------------------------------------
// Test: PING_INTERNAL (0x20)
// Measures internal ping processing time (no actual I/O)
// ---------------------------------------------------------------------------
static bool test_ping_internal() {
    // Simulate ping processing without actual serial I/O
    volatile uint32_t ts = micros();
    volatile uint32_t response = ts + 1;  // Minimal computation
    (void)response;
    return true;
}

static BenchmarkRegistrar reg_ping_internal{
    TestInfo{
        TestId::PING_INTERNAL,
        "PING_INTERNAL",
        "Internal ping processing",
        TestInfo::FLAG_RT_SAFE | TestInfo::FLAG_BOOT_TEST
    },
    test_ping_internal
};

// ---------------------------------------------------------------------------
// Test: CMD_DECODE (0x21)
// Measures JSON command decode time
// ---------------------------------------------------------------------------
#include <ArduinoJson.h>

static const char* TEST_JSON = R"({"cmd":"CMD_SERVO_SET_ANGLE","channel":0,"angle":90.0})";

static bool test_cmd_decode() {
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, TEST_JSON);
    if (err) return false;

    // Access fields to simulate actual decode
    const char* cmd = doc["cmd"] | "";
    int channel = doc["channel"] | -1;
    float angle = doc["angle"] | 0.0f;

    (void)cmd;
    (void)channel;
    (void)angle;

    return true;
}

static BenchmarkRegistrar reg_cmd_decode{
    TestInfo{
        TestId::CMD_DECODE,
        "CMD_DECODE",
        "JSON command decode time",
        0  // Not RT-safe (allocates)
    },
    test_cmd_decode
};

// ---------------------------------------------------------------------------
// Test: TELEM_ENCODE (0x22)
// Measures binary telemetry encode time
// ---------------------------------------------------------------------------
static bool test_telem_encode() {
    // Simulate binary telemetry encoding
    uint8_t buffer[64];
    size_t offset = 0;

    // Pack some test data (little-endian)
    uint32_t ts = millis();
    memcpy(buffer + offset, &ts, sizeof(ts)); offset += sizeof(ts);

    float values[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    for (int i = 0; i < 4; i++) {
        memcpy(buffer + offset, &values[i], sizeof(float));
        offset += sizeof(float);
    }

    // Prevent optimization
    volatile uint8_t check = buffer[0];
    (void)check;

    return offset == 20;
}

static BenchmarkRegistrar reg_telem_encode{
    TestInfo{
        TestId::TELEM_ENCODE,
        "TELEM_ENCODE",
        "Binary telemetry encode",
        TestInfo::FLAG_RT_SAFE
    },
    test_telem_encode
};

// ---------------------------------------------------------------------------
// Test: TELEM_JSON_ENCODE (0x23)
// Measures JSON telemetry encode time
// ---------------------------------------------------------------------------
static bool test_telem_json_encode() {
    JsonDocument doc;

    doc["ts"] = millis();
    doc["v1"] = 1.0f;
    doc["v2"] = 2.0f;
    doc["v3"] = 3.0f;
    doc["v4"] = 4.0f;

    char buffer[128];
    size_t len = serializeJson(doc, buffer, sizeof(buffer));

    return len > 0;
}

static BenchmarkRegistrar reg_telem_json_encode{
    TestInfo{
        TestId::TELEM_JSON_ENCODE,
        "TELEM_JSON",
        "JSON telemetry encode",
        0  // Not RT-safe (allocates)
    },
    test_telem_json_encode
};

// ---------------------------------------------------------------------------
// Test: PID_STEP (0x30)
// Measures PID controller step time
// ---------------------------------------------------------------------------
#if HAS_DC_MOTOR || HAS_MOTION_CONTROLLER
#include "motor/PID.h"

static PID bench_pid(1.0f, 0.1f, 0.01f);

static bool test_pid_step() {
    static float target = 0.0f;
    static float meas = 0.0f;

    // Simulate varying inputs
    target = (target + 0.1f);
    if (target > 10.0f) target = 0.0f;
    meas = target * 0.9f;  // Simulated lag

    float output = bench_pid.compute(target, meas, 0.001f);  // 1ms dt
    (void)output;

    return true;
}

static BenchmarkRegistrar reg_pid_step{
    TestInfo{
        TestId::PID_STEP,
        "PID_STEP",
        "PID controller step()",
        TestInfo::FLAG_RT_SAFE
    },
    test_pid_step
};
#endif  // HAS_DC_MOTOR || HAS_MOTION_CONTROLLER

// ---------------------------------------------------------------------------
// Test: OBSERVER_UPDATE (0x31)
// Measures state observer update time
// NOTE: Disabled - requires complex setup with SignalBus and configuration
// ---------------------------------------------------------------------------
// #if HAS_OBSERVER
// static bool test_observer_update() {
//     // Observer tests require SignalBus setup
//     return true;
// }
//
// static BenchmarkRegistrar reg_observer_update{
//     TestInfo{
//         TestId::OBSERVER_UPDATE,
//         "OBSERVER",
//         "Observer update()",
//         TestInfo::FLAG_RT_SAFE
//     },
//     test_observer_update
// };
// #endif  // HAS_OBSERVER

// ---------------------------------------------------------------------------
// Test: KERNEL_STEP (0x32)
// Measures full ControlKernel step time
// NOTE: Disabled - requires SignalBus, arm state, and full setup
// ---------------------------------------------------------------------------
// #if HAS_CONTROL_KERNEL
// static bool test_kernel_step() {
//     // ControlKernel::step requires (now_ms, dt_s, signals, is_armed, is_active)
//     return true;
// }
//
// static BenchmarkRegistrar reg_kernel_step{
//     TestInfo{
//         TestId::KERNEL_STEP,
//         "KERNEL_STEP",
//         "Full ControlKernel step",
//         TestInfo::FLAG_RT_SAFE
//     },
//     test_kernel_step
// };
// #endif  // HAS_CONTROL_KERNEL

// ---------------------------------------------------------------------------
// Test: HEAP_ALLOC_SMALL (0x40)
// Measures small heap allocation time
// ---------------------------------------------------------------------------
static bool test_heap_alloc_small() {
    void* ptr = malloc(64);
    if (!ptr) return false;
    memset(ptr, 0xAA, 64);  // Touch memory
    free(ptr);
    return true;
}

static BenchmarkRegistrar reg_heap_alloc_small{
    TestInfo{
        TestId::HEAP_ALLOC_SMALL,
        "HEAP_64B",
        "64-byte heap alloc/free",
        TestInfo::FLAG_SLOW  // Not RT-safe
    },
    test_heap_alloc_small
};

// ---------------------------------------------------------------------------
// Test: HEAP_ALLOC_MEDIUM (0x41)
// Measures medium heap allocation time
// ---------------------------------------------------------------------------
static bool test_heap_alloc_medium() {
    void* ptr = malloc(512);
    if (!ptr) return false;
    memset(ptr, 0xBB, 512);  // Touch memory
    free(ptr);
    return true;
}

static BenchmarkRegistrar reg_heap_alloc_medium{
    TestInfo{
        TestId::HEAP_ALLOC_MEDIUM,
        "HEAP_512B",
        "512-byte heap alloc/free",
        TestInfo::FLAG_SLOW  // Not RT-safe
    },
    test_heap_alloc_medium
};

}  // namespace benchmark

#endif  // FEATURE_BENCHMARK
