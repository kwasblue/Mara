// src/benchmark/BenchmarkModule.cpp
// Benchmark module implementation

#ifdef FEATURE_BENCHMARK

#include "benchmark/BenchmarkModule.h"
#include "core/ServiceContext.h"
#include "core/EventBus.h"
#include "module/TelemetryModule.h"
#include "telemetry/TelemetrySections.h"
#include "core/Debug.h"
#include <Arduino.h>

namespace benchmark {

// Boot test sequence - tests to run automatically at startup
static constexpr TestId BOOT_TESTS[] = {
    TestId::LOOP_TIMING,
    TestId::SIGNAL_BUS_LATENCY,
    TestId::PING_INTERNAL
};
static constexpr size_t BOOT_TEST_COUNT = sizeof(BOOT_TESTS) / sizeof(BOOT_TESTS[0]);

BenchmarkModule::BenchmarkModule(EventBus& bus)
    : bus_(bus)
{
    // Initialize result history
    for (auto& r : results_) {
        r.clear();
    }
}

void BenchmarkModule::init(mara::ServiceContext& ctx) {
    // Get telemetry module if available
    if (ctx.telemetry) {
        registerTelemetry(ctx.telemetry);
    }
}

void BenchmarkModule::setup() {
    DBG_PRINTF("[BENCH] Module setup, %zu tests registered\n",
               BenchmarkRunner::instance().registeredCount());

    // Schedule boot tests
    bootTestsComplete_ = false;
    bootTestIndex_ = 0;
    lastRunMs_ = millis();
}

void BenchmarkModule::loop(uint32_t now_ms) {
    // Rate limit processing
    if (now_ms - lastRunMs_ < MIN_RUN_INTERVAL_MS) {
        return;
    }
    lastRunMs_ = now_ms;

    // If not actively running a benchmark, check queue or boot tests
    if (state_ != BenchState::RUNNING) {
        // Boot tests first
        if (!bootTestsComplete_) {
            runNextBootTest();
            return;
        }

        // Then process queue
        if (queueCount_ > 0) {
            processQueue(now_ms);
        } else if (state_ != BenchState::IDLE) {
            state_ = BenchState::IDLE;
            activeTest_ = TestId::UNKNOWN;
        }
    }
}

void BenchmarkModule::handleEvent(const Event& evt) {
    // Could respond to events if needed
    (void)evt;
}

bool BenchmarkModule::queueBenchmark(const BenchConfig& config) {
    if (queueCount_ >= MAX_QUEUE_DEPTH) {
        DBG_PRINTF("[BENCH] Queue full, cannot add test 0x%02X\n",
                   static_cast<int>(config.test_id));
        return false;
    }

    // Verify test exists
    if (!BenchmarkRunner::instance().getTestInfo(config.test_id)) {
        DBG_PRINTF("[BENCH] Unknown test 0x%02X\n",
                   static_cast<int>(config.test_id));
        return false;
    }

    return enqueue(config);
}

void BenchmarkModule::cancelAll() {
    // Cancel running benchmark
    BenchmarkRunner::instance().cancel();

    // Clear queue
    queueHead_ = 0;
    queueTail_ = 0;
    queueCount_ = 0;

    state_ = BenchState::IDLE;
    activeTest_ = TestId::UNKNOWN;

    DBG_PRINTF("[BENCH] All benchmarks cancelled\n");
}

void BenchmarkModule::runBootTests() {
    bootTestsComplete_ = false;
    bootTestIndex_ = 0;
    DBG_PRINTF("[BENCH] Boot tests scheduled\n");
}

const BenchResult* BenchmarkModule::getLatestResult() const {
    if (resultCount_ == 0) {
        return nullptr;
    }
    // Latest is at (head - 1 + SIZE) % SIZE
    size_t idx = (resultHead_ + RESULT_HISTORY_SIZE - 1) % RESULT_HISTORY_SIZE;
    return &results_[idx];
}

size_t BenchmarkModule::getResults(const BenchResult** out, size_t max_count) const {
    size_t count = 0;
    size_t actual_count = std::min(resultCount_, max_count);

    // Start from oldest result
    size_t start = (resultHead_ + RESULT_HISTORY_SIZE - resultCount_) % RESULT_HISTORY_SIZE;

    for (size_t i = 0; i < actual_count; i++) {
        size_t idx = (start + i) % RESULT_HISTORY_SIZE;
        out[count++] = &results_[idx];
    }

    return count;
}

void BenchmarkModule::registerTelemetry(TelemetryModule* telemetry) {
    telemetry_ = telemetry;
    if (!telemetry_) return;

    // Register binary telemetry provider for TELEM_BENCHMARK (0x13)
    telemetry_->registerBinProvider(0x13, [this](std::vector<uint8_t>& out) {
        provideTelemetry(out);
    });

    DBG_PRINTF("[BENCH] Telemetry provider registered\n");
}

bool BenchmarkModule::enqueue(const BenchConfig& config) {
    if (queueCount_ >= MAX_QUEUE_DEPTH) {
        return false;
    }

    queue_[queueTail_] = config;
    queueTail_ = (queueTail_ + 1) % MAX_QUEUE_DEPTH;
    queueCount_++;

    if (state_ == BenchState::IDLE) {
        state_ = BenchState::QUEUED;
    }

    DBG_PRINTF("[BENCH] Queued test 0x%02X, depth=%zu\n",
               static_cast<int>(config.test_id), queueCount_);
    return true;
}

bool BenchmarkModule::dequeue(BenchConfig& config) {
    if (queueCount_ == 0) {
        return false;
    }

    config = queue_[queueHead_];
    queueHead_ = (queueHead_ + 1) % MAX_QUEUE_DEPTH;
    queueCount_--;

    return true;
}

void BenchmarkModule::storeResult(const BenchResult& result) {
    results_[resultHead_] = result;
    resultHead_ = (resultHead_ + 1) % RESULT_HISTORY_SIZE;
    if (resultCount_ < RESULT_HISTORY_SIZE) {
        resultCount_++;
    }
}

void BenchmarkModule::processQueue(uint32_t now_ms) {
    BenchConfig config;
    if (!dequeue(config)) {
        return;
    }

    state_ = BenchState::RUNNING;
    activeTest_ = config.test_id;

    DBG_PRINTF("[BENCH] Running test 0x%02X, %u iterations\n",
               static_cast<int>(config.test_id), config.iterations);

    BenchResult result;
    bool success = BenchmarkRunner::instance().run(config, result);

    // Store result
    storeResult(result);

    // Reset active test
    activeTest_ = TestId::UNKNOWN;

    // Update state - use IDLE to allow next queue processing
    if (queueCount_ > 0) {
        state_ = BenchState::IDLE;  // Will process next item on next loop
    } else {
        state_ = success ? BenchState::COMPLETE : BenchState::ERROR;
    }

    // Publish event
    Event evt;
    evt.type = EventType::BENCHMARK_COMPLETE;
    evt.timestamp_ms = now_ms;
    evt.payload.u8 = static_cast<uint8_t>(result.test_id);
    evt.payload.i32 = static_cast<int32_t>(result.mean_us);
    bus_.publish(evt);

    DBG_PRINTF("[BENCH] Test 0x%02X complete: mean=%luus, p99=%luus, queue=%zu\n",
               static_cast<int>(result.test_id),
               (unsigned long)result.mean_us,
               (unsigned long)result.p99_us,
               queueCount_);
}

void BenchmarkModule::runNextBootTest() {
    if (bootTestIndex_ >= BOOT_TEST_COUNT) {
        bootTestsComplete_ = true;
        state_ = BenchState::IDLE;
        activeTest_ = TestId::UNKNOWN;
        DBG_PRINTF("[BENCH] Boot tests complete\n");
        return;
    }

    TestId testId = BOOT_TESTS[bootTestIndex_];

    // Check if test is registered
    if (!BenchmarkRunner::instance().getTestInfo(testId)) {
        bootTestIndex_++;
        return;
    }

    // Run with minimal iterations for quick boot
    BenchConfig config = BenchConfig::defaults(testId);
    config.iterations = 50;
    config.warmup = 5;

    state_ = BenchState::RUNNING;
    activeTest_ = testId;

    DBG_PRINTF("[BENCH] Boot test %u/%zu: 0x%02X\n",
               bootTestIndex_ + 1, BOOT_TEST_COUNT,
               static_cast<int>(testId));

    BenchResult result;
    BenchmarkRunner::instance().run(config, result);
    storeResult(result);

    bootTestIndex_++;

    // Reset state after boot test completes
    state_ = BenchState::IDLE;
    activeTest_ = TestId::UNKNOWN;
}

void BenchmarkModule::provideTelemetry(std::vector<uint8_t>& out) {
    // Header: state(1) + active_test(1) + queue_depth(1) + result_count(1) = 4 bytes
    out.push_back(static_cast<uint8_t>(state_));
    out.push_back(static_cast<uint8_t>(activeTest_));
    out.push_back(static_cast<uint8_t>(queueCount_));
    out.push_back(static_cast<uint8_t>(resultCount_));

    // Include latest result if available (56 bytes)
    const BenchResult* latest = getLatestResult();
    if (latest) {
        const uint8_t* ptr = reinterpret_cast<const uint8_t*>(latest);
        for (size_t i = 0; i < sizeof(BenchResult); i++) {
            out.push_back(ptr[i]);
        }
    }
}

}  // namespace benchmark

#endif  // FEATURE_BENCHMARK
