// src/benchmark/BenchmarkRunner.cpp
// Benchmark execution engine implementation

#ifdef FEATURE_BENCHMARK

#include "benchmark/BenchmarkRunner.h"
#include "core/Clock.h"
#include <algorithm>
#include <cmath>

namespace benchmark {

BenchmarkRunner& BenchmarkRunner::instance() {
    static BenchmarkRunner runner;
    return runner;
}

bool BenchmarkRunner::registerTest(const TestInfo& info, TestFunc func) {
    if (registeredCount_ >= MAX_REGISTERED_TESTS) {
        return false;
    }

    // Check for duplicate
    if (findTest(info.id) != nullptr) {
        return false;
    }

    tests_[registeredCount_] = RegisteredTest{
        .info = info,
        .func = func,
        .registered = true
    };
    registeredCount_++;
    return true;
}

const TestInfo* BenchmarkRunner::getTestInfo(TestId id) const {
    const RegisteredTest* test = findTest(id);
    return test ? &test->info : nullptr;
}

size_t BenchmarkRunner::getRegisteredTests(const TestInfo** out, size_t max_count) const {
    size_t count = 0;
    for (size_t i = 0; i < registeredCount_ && count < max_count; i++) {
        if (tests_[i].registered) {
            out[count++] = &tests_[i].info;
        }
    }
    return count;
}

const RegisteredTest* BenchmarkRunner::findTest(TestId id) const {
    for (size_t i = 0; i < registeredCount_; i++) {
        if (tests_[i].registered && tests_[i].info.id == id) {
            return &tests_[i];
        }
    }
    return nullptr;
}

RegisteredTest* BenchmarkRunner::findTest(TestId id) {
    for (size_t i = 0; i < registeredCount_; i++) {
        if (tests_[i].registered && tests_[i].info.id == id) {
            return &tests_[i];
        }
    }
    return nullptr;
}

bool BenchmarkRunner::run(const BenchConfig& config, BenchResult& result) {
    result.clear();
    result.test_id = config.test_id;

    // Find the test
    const RegisteredTest* test = findTest(config.test_id);
    if (!test) {
        result.state = BenchState::ERROR;
        result.error = BenchError::UNKNOWN_TEST;
        result.timestamp_ms = mara::getSystemClock().millis();
        return false;
    }

    // Mark as running
    running_ = true;
    cancelled_ = false;
    result.state = BenchState::RUNNING;

    // Reset sample buffer
    sampleCount_ = 0;

    // Warmup iterations (not timed)
    for (uint16_t i = 0; i < config.warmup && !cancelled_; i++) {
        test->func();
    }

    if (cancelled_) {
        result.state = BenchState::ERROR;
        result.error = BenchError::CANCELLED;
        result.timestamp_ms = mara::getSystemClock().millis();
        running_ = false;
        return false;
    }

    // Timed iterations
    uint32_t total_start_us = mara::getSystemClock().micros();
    uint32_t budget_violations = 0;

    for (uint16_t i = 0; i < config.iterations && !cancelled_; i++) {
        uint32_t start_us = mara::getSystemClock().micros();

        bool success = test->func();

        uint32_t elapsed_us = mara::getSystemClock().micros() - start_us;

        // Only record successful iterations
        if (success && sampleCount_ < MAX_SAMPLE_COUNT) {
            samples_[sampleCount_++] = elapsed_us;
        }

        // Check budget
        if (config.budget_us > 0 && elapsed_us > config.budget_us) {
            budget_violations++;
        }
    }

    uint32_t total_elapsed_us = mara::getSystemClock().micros() - total_start_us;
    running_ = false;

    if (cancelled_) {
        result.state = BenchState::ERROR;
        result.error = BenchError::CANCELLED;
        result.timestamp_ms = mara::getSystemClock().millis();
        return false;
    }

    // Compute statistics
    result.samples = static_cast<uint16_t>(sampleCount_);
    result.total_us = total_elapsed_us;
    result.budget_violations = static_cast<uint16_t>(budget_violations);

    if (sampleCount_ > 0) {
        computeStats(result);
    }

    result.state = BenchState::COMPLETE;
    result.timestamp_ms = mara::getSystemClock().millis();

    // Throughput (stored as Hz * 100 for precision without floats)
    if (total_elapsed_us > 0 && config.iterations > 0) {
        uint32_t throughput_x100 = (static_cast<uint64_t>(config.iterations) * 100000000ULL) / total_elapsed_us;
        result.extra1 = throughput_x100;
    }

    return true;
}

void BenchmarkRunner::cancel() {
    cancelled_ = true;
}

void BenchmarkRunner::computeStats(BenchResult& result) {
    if (sampleCount_ == 0) return;

    // Compute min, max, sum
    uint32_t min_val = samples_[0];
    uint32_t max_val = samples_[0];
    uint64_t sum = 0;

    for (size_t i = 0; i < sampleCount_; i++) {
        uint32_t v = samples_[i];
        if (v < min_val) min_val = v;
        if (v > max_val) max_val = v;
        sum += v;
    }

    result.min_us = min_val;
    result.max_us = max_val;
    result.mean_us = static_cast<uint32_t>(sum / sampleCount_);

    // Percentiles using quickselect
    // Note: quickSelect modifies samples_ array, but we're done with it
    result.p50_us = quickSelect(sampleCount_ / 2);
    result.p95_us = quickSelect((sampleCount_ * 95) / 100);
    result.p99_us = quickSelect((sampleCount_ * 99) / 100);

    // Standard deviation (jitter)
    // Using integer math to avoid float
    if (sampleCount_ > 1) {
        uint64_t sum_sq_diff = 0;
        int32_t mean = static_cast<int32_t>(result.mean_us);
        for (size_t i = 0; i < sampleCount_; i++) {
            int32_t diff = static_cast<int32_t>(samples_[i]) - mean;
            sum_sq_diff += static_cast<uint64_t>(diff * diff);
        }
        uint64_t variance = sum_sq_diff / (sampleCount_ - 1);
        // Integer square root approximation
        uint32_t stddev = 0;
        if (variance > 0) {
            // Newton's method for integer sqrt
            uint64_t x = variance;
            uint64_t y = (x + 1) / 2;
            while (y < x) {
                x = y;
                y = (x + variance / x) / 2;
            }
            stddev = static_cast<uint32_t>(x);
        }
        result.jitter_us = stddev;
    }
}

// Quickselect algorithm for O(n) expected time percentile calculation
// Modifies the samples_ array in place
uint32_t BenchmarkRunner::quickSelect(size_t k) {
    if (sampleCount_ == 0) return 0;
    if (k >= sampleCount_) k = sampleCount_ - 1;

    size_t left = 0;
    size_t right = sampleCount_ - 1;

    while (left < right) {
        // Partition around pivot (median-of-three for better performance)
        size_t mid = left + (right - left) / 2;

        // Sort left, mid, right
        if (samples_[mid] < samples_[left]) std::swap(samples_[left], samples_[mid]);
        if (samples_[right] < samples_[left]) std::swap(samples_[left], samples_[right]);
        if (samples_[right] < samples_[mid]) std::swap(samples_[mid], samples_[right]);

        uint32_t pivot = samples_[mid];
        std::swap(samples_[mid], samples_[right - 1]);

        size_t i = left;
        size_t j = right - 1;

        while (true) {
            while (samples_[++i] < pivot) {}
            while (samples_[--j] > pivot) {}
            if (i >= j) break;
            std::swap(samples_[i], samples_[j]);
        }

        std::swap(samples_[i], samples_[right - 1]);

        if (k < i) {
            right = i - 1;
        } else if (k > i) {
            left = i + 1;
        } else {
            return samples_[i];
        }
    }

    return samples_[left];
}

}  // namespace benchmark

#endif  // FEATURE_BENCHMARK
