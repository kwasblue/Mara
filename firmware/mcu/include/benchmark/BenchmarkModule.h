// include/benchmark/BenchmarkModule.h
// IModule implementation for benchmark subsystem

#pragma once

#ifdef FEATURE_BENCHMARK

#include <array>
#include "core/IModule.h"
#include "core/Event.h"
#include "benchmark/BenchmarkTypes.h"
#include "benchmark/BenchmarkRunner.h"

// Forward declarations
class EventBus;
class TelemetryModule;

namespace benchmark {

/**
 * BenchmarkModule - Manages benchmark lifecycle and queue.
 *
 * Features:
 * - Ring buffer queue for pending benchmarks
 * - Ring buffer for result history (8 results)
 * - Boot-time self-test sequence
 * - Runs on MAIN loop domain (low priority)
 * - Telemetry integration via binary provider
 *
 * Usage:
 *   // Add to module list
 *   host.addModule(&benchmarkModule);
 *
 *   // Queue a benchmark via command handler
 *   module.queueBenchmark(config);
 *
 *   // Check status
 *   module.getState();
 *   module.getQueueDepth();
 */
class BenchmarkModule : public IModule {
public:
    explicit BenchmarkModule(EventBus& bus);

    // IModule interface
    void init(mara::ServiceContext& ctx) override;
    void setup() override;
    void loop(uint32_t now_ms) override;
    const char* name() const override { return "BenchmarkModule"; }
    void handleEvent(const Event& evt) override;
    int priority() const override { return 150; }  // Low priority, runs after others
    LoopDomain domain() const override { return LoopDomain::MAIN; }

    // Benchmark queue management
    bool queueBenchmark(const BenchConfig& config);
    void cancelAll();
    void runBootTests();

    // State queries
    BenchState getState() const { return state_; }
    TestId getActiveTest() const { return activeTest_; }
    size_t getQueueDepth() const { return queueCount_; }
    size_t getResultCount() const { return resultCount_; }

    // Result access
    const BenchResult* getLatestResult() const;
    size_t getResults(const BenchResult** out, size_t max_count) const;

    // Telemetry provider registration
    void registerTelemetry(TelemetryModule* telemetry);

private:
    // Ring buffer helpers
    bool enqueue(const BenchConfig& config);
    bool dequeue(BenchConfig& config);
    void storeResult(const BenchResult& result);

    // Process next queued benchmark
    void processQueue(uint32_t now_ms);

    // Boot test sequence
    void runNextBootTest();

    // Telemetry provider callback
    void provideTelemetry(std::vector<uint8_t>& out);

    EventBus& bus_;
    TelemetryModule* telemetry_ = nullptr;

    // State
    BenchState state_ = BenchState::IDLE;
    TestId activeTest_ = TestId::UNKNOWN;
    bool bootTestsComplete_ = false;
    uint8_t bootTestIndex_ = 0;

    // Queue (ring buffer)
    std::array<BenchConfig, MAX_QUEUE_DEPTH> queue_{};
    size_t queueHead_ = 0;
    size_t queueTail_ = 0;
    size_t queueCount_ = 0;

    // Result history (ring buffer)
    std::array<BenchResult, RESULT_HISTORY_SIZE> results_{};
    size_t resultHead_ = 0;
    size_t resultCount_ = 0;

    // Timing
    uint32_t lastRunMs_ = 0;
    static constexpr uint32_t MIN_RUN_INTERVAL_MS = 10;  // Don't hog CPU
};

}  // namespace benchmark

#endif  // FEATURE_BENCHMARK
