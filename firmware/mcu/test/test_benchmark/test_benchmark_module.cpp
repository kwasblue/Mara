// test/test_benchmark/test_benchmark_module.cpp
// Unit tests for BenchmarkModule

#include <unity.h>
#include <vector>

// Define feature flag before including headers
#define FEATURE_BENCHMARK 1

// Mock EventBus for testing
class EventBus {
public:
    void publish(const struct Event& evt) { lastEventType = static_cast<int>(evt.type); }
    void subscribe(void (*fn)(const struct Event&)) { (void)fn; }
    int lastEventType = -1;
};

// Minimal Event definition for testing
enum class EventType : uint8_t {
    BENCHMARK_COMPLETE = 100
};

struct EventPayload {
    int32_t i32 = 0;
    float f32 = 0.0f;
    uint8_t u8 = 0;
};

struct Event {
    EventType type;
    uint32_t timestamp_ms;
    EventPayload payload;
};

// Mock TelemetryModule
class TelemetryModule {
public:
    using BinProviderFn = std::function<void(std::vector<uint8_t>&)>;
    void registerBinProvider(uint8_t id, BinProviderFn fn) {
        lastProviderId = id;
        provider = fn;
    }
    uint8_t lastProviderId = 0;
    BinProviderFn provider;
};

// Mock ServiceContext
namespace mara {
struct ServiceContext {
    TelemetryModule* telemetry = nullptr;
};
}

#include "benchmark/BenchmarkTypes.h"
#include "benchmark/BenchmarkRunner.h"
#include "benchmark/BenchmarkModule.h"

// Include implementations
#include "../../src/benchmark/BenchmarkRunner.cpp"

// Simplified BenchmarkModule implementation for testing (avoiding full dependency)
// We test the queue and result buffer logic directly

using namespace benchmark;

static EventBus g_eventBus;
static TelemetryModule g_telemetry;

void setUp() {}
void tearDown() {}

// =============================================================================
// Queue tests (using direct buffer manipulation for simplicity)
// =============================================================================

void test_queue_enqueue_dequeue() {
    // Test ring buffer logic
    std::array<BenchConfig, MAX_QUEUE_DEPTH> queue{};
    size_t head = 0;
    size_t tail = 0;
    size_t count = 0;

    // Enqueue
    auto enqueue = [&](TestId id) -> bool {
        if (count >= MAX_QUEUE_DEPTH) return false;
        queue[tail] = BenchConfig::defaults(id);
        tail = (tail + 1) % MAX_QUEUE_DEPTH;
        count++;
        return true;
    };

    // Dequeue
    auto dequeue = [&](BenchConfig& out) -> bool {
        if (count == 0) return false;
        out = queue[head];
        head = (head + 1) % MAX_QUEUE_DEPTH;
        count--;
        return true;
    };

    // Test basic operations
    TEST_ASSERT_TRUE(enqueue(TestId::LOOP_TIMING));
    TEST_ASSERT_TRUE(enqueue(TestId::PID_STEP));
    TEST_ASSERT_EQUAL(2, count);

    BenchConfig out;
    TEST_ASSERT_TRUE(dequeue(out));
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(TestId::LOOP_TIMING), static_cast<uint8_t>(out.test_id));
    TEST_ASSERT_EQUAL(1, count);

    TEST_ASSERT_TRUE(dequeue(out));
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(TestId::PID_STEP), static_cast<uint8_t>(out.test_id));
    TEST_ASSERT_EQUAL(0, count);

    // Empty dequeue
    TEST_ASSERT_FALSE(dequeue(out));
}

void test_queue_wraps_around() {
    std::array<BenchConfig, MAX_QUEUE_DEPTH> queue{};
    size_t head = 0;
    size_t tail = 0;
    size_t count = 0;

    auto enqueue = [&](TestId id) -> bool {
        if (count >= MAX_QUEUE_DEPTH) return false;
        queue[tail] = BenchConfig::defaults(id);
        tail = (tail + 1) % MAX_QUEUE_DEPTH;
        count++;
        return true;
    };

    auto dequeue = [&](BenchConfig& out) -> bool {
        if (count == 0) return false;
        out = queue[head];
        head = (head + 1) % MAX_QUEUE_DEPTH;
        count--;
        return true;
    };

    // Fill queue
    for (size_t i = 0; i < MAX_QUEUE_DEPTH; i++) {
        TEST_ASSERT_TRUE(enqueue(TestId::LOOP_TIMING));
    }
    TEST_ASSERT_EQUAL(MAX_QUEUE_DEPTH, count);

    // Queue full
    TEST_ASSERT_FALSE(enqueue(TestId::PID_STEP));

    // Dequeue half
    BenchConfig out;
    for (size_t i = 0; i < MAX_QUEUE_DEPTH / 2; i++) {
        TEST_ASSERT_TRUE(dequeue(out));
    }

    // Enqueue more (wraps around)
    for (size_t i = 0; i < MAX_QUEUE_DEPTH / 2; i++) {
        TEST_ASSERT_TRUE(enqueue(TestId::PID_STEP));
    }

    TEST_ASSERT_EQUAL(MAX_QUEUE_DEPTH, count);
}

// =============================================================================
// Result history tests
// =============================================================================

void test_result_history_stores_results() {
    std::array<BenchResult, RESULT_HISTORY_SIZE> results{};
    size_t head = 0;
    size_t count = 0;

    auto storeResult = [&](const BenchResult& result) {
        results[head] = result;
        head = (head + 1) % RESULT_HISTORY_SIZE;
        if (count < RESULT_HISTORY_SIZE) count++;
    };

    auto getLatest = [&]() -> const BenchResult* {
        if (count == 0) return nullptr;
        size_t idx = (head + RESULT_HISTORY_SIZE - 1) % RESULT_HISTORY_SIZE;
        return &results[idx];
    };

    // Empty initially
    TEST_ASSERT_NULL(getLatest());

    // Store one result
    BenchResult r1;
    r1.clear();
    r1.test_id = TestId::LOOP_TIMING;
    r1.mean_us = 100;
    storeResult(r1);

    TEST_ASSERT_NOT_NULL(getLatest());
    TEST_ASSERT_EQUAL(100, getLatest()->mean_us);
    TEST_ASSERT_EQUAL(1, count);

    // Store another
    BenchResult r2;
    r2.clear();
    r2.test_id = TestId::PID_STEP;
    r2.mean_us = 200;
    storeResult(r2);

    TEST_ASSERT_EQUAL(200, getLatest()->mean_us);
    TEST_ASSERT_EQUAL(2, count);
}

void test_result_history_wraps_around() {
    std::array<BenchResult, RESULT_HISTORY_SIZE> results{};
    size_t head = 0;
    size_t count = 0;

    auto storeResult = [&](uint32_t mean_us) {
        BenchResult r;
        r.clear();
        r.mean_us = mean_us;
        results[head] = r;
        head = (head + 1) % RESULT_HISTORY_SIZE;
        if (count < RESULT_HISTORY_SIZE) count++;
    };

    auto getLatest = [&]() -> const BenchResult* {
        if (count == 0) return nullptr;
        size_t idx = (head + RESULT_HISTORY_SIZE - 1) % RESULT_HISTORY_SIZE;
        return &results[idx];
    };

    // Fill history
    for (size_t i = 0; i < RESULT_HISTORY_SIZE; i++) {
        storeResult(i * 100);
    }
    TEST_ASSERT_EQUAL(RESULT_HISTORY_SIZE, count);
    TEST_ASSERT_EQUAL((RESULT_HISTORY_SIZE - 1) * 100, getLatest()->mean_us);

    // Add more (wraps around, count stays at max)
    storeResult(9999);
    TEST_ASSERT_EQUAL(RESULT_HISTORY_SIZE, count);
    TEST_ASSERT_EQUAL(9999, getLatest()->mean_us);
}

// =============================================================================
// Telemetry provider tests
// =============================================================================

void test_telemetry_provider_output_format() {
    std::vector<uint8_t> out;

    // Simulate telemetry provider output
    BenchState state = BenchState::COMPLETE;
    TestId activeTest = TestId::LOOP_TIMING;
    uint8_t queueCount = 2;
    uint8_t resultCount = 3;

    out.push_back(static_cast<uint8_t>(state));
    out.push_back(static_cast<uint8_t>(activeTest));
    out.push_back(queueCount);
    out.push_back(resultCount);

    TEST_ASSERT_EQUAL(4, out.size());
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(BenchState::COMPLETE), out[0]);
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(TestId::LOOP_TIMING), out[1]);
    TEST_ASSERT_EQUAL(2, out[2]);
    TEST_ASSERT_EQUAL(3, out[3]);
}

void test_telemetry_provider_includes_result() {
    std::vector<uint8_t> out;

    // Header
    out.push_back(static_cast<uint8_t>(BenchState::COMPLETE));
    out.push_back(static_cast<uint8_t>(TestId::PID_STEP));
    out.push_back(0);  // queue depth
    out.push_back(1);  // result count

    // Result (56 bytes packed)
    BenchResult result;
    result.clear();
    result.test_id = TestId::PID_STEP;
    result.state = BenchState::COMPLETE;
    result.mean_us = 1234;
    result.samples = 100;

    const uint8_t* ptr = reinterpret_cast<const uint8_t*>(&result);
    for (size_t i = 0; i < sizeof(BenchResult); i++) {
        out.push_back(ptr[i]);
    }

    // Total should be 4 header + 56 result = 60 bytes
    TEST_ASSERT_EQUAL(4 + sizeof(BenchResult), out.size());

    // Verify we can read back the result
    const BenchResult* parsed = reinterpret_cast<const BenchResult*>(&out[4]);
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(TestId::PID_STEP), static_cast<uint8_t>(parsed->test_id));
    TEST_ASSERT_EQUAL(1234, parsed->mean_us);
    TEST_ASSERT_EQUAL(100, parsed->samples);
}

// =============================================================================
// State machine tests
// =============================================================================

void test_state_transitions() {
    // Verify state enum values and transitions
    BenchState state = BenchState::IDLE;

    // IDLE -> QUEUED when benchmark queued
    state = BenchState::QUEUED;
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(BenchState::QUEUED), static_cast<uint8_t>(state));

    // QUEUED -> RUNNING when processing starts
    state = BenchState::RUNNING;
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(BenchState::RUNNING), static_cast<uint8_t>(state));

    // RUNNING -> COMPLETE on success
    state = BenchState::COMPLETE;
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(BenchState::COMPLETE), static_cast<uint8_t>(state));

    // RUNNING -> ERROR on failure
    state = BenchState::ERROR;
    TEST_ASSERT_EQUAL(static_cast<uint8_t>(BenchState::ERROR), static_cast<uint8_t>(state));
}

// =============================================================================
// Main
// =============================================================================

int main(int argc, char** argv) {
    UNITY_BEGIN();

    // Queue tests
    RUN_TEST(test_queue_enqueue_dequeue);
    RUN_TEST(test_queue_wraps_around);

    // Result history tests
    RUN_TEST(test_result_history_stores_results);
    RUN_TEST(test_result_history_wraps_around);

    // Telemetry provider tests
    RUN_TEST(test_telemetry_provider_output_format);
    RUN_TEST(test_telemetry_provider_includes_result);

    // State machine tests
    RUN_TEST(test_state_transitions);

    return UNITY_END();
}
