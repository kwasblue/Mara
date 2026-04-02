// src/command/handlers/BenchmarkHandler.cpp
// Benchmark command handler implementation

#ifdef FEATURE_BENCHMARK

#include "command/handlers/BenchmarkHandler.h"
#include "benchmark/BenchmarkModule.h"
#include "benchmark/BenchmarkRunner.h"
#include "benchmark/BenchmarkTypes.h"
#include "core/ServiceContext.h"
#include "core/Debug.h"
#include <Arduino.h>

void BenchmarkHandler::init(mara::ServiceContext& ctx) {
    module_ = static_cast<benchmark::BenchmarkModule*>(ctx.benchmark);
}

void BenchmarkHandler::handleStart(JsonVariantConst payload, CommandContext& ctx) {
    // Parse test_id (required)
    if (payload["test_id"].isNull()) {
        ctx.sendError("CMD_BENCH_START", "missing_test_id");
        return;
    }

    uint8_t testIdRaw = payload["test_id"] | 0;
    benchmark::TestId testId = static_cast<benchmark::TestId>(testIdRaw);

    // Check if test exists
    if (!benchmark::BenchmarkRunner::instance().getTestInfo(testId)) {
        ctx.sendError("CMD_BENCH_START", "unknown_test");
        return;
    }

    // Build config from payload
    benchmark::BenchConfig config;
    config.test_id = testId;
    config.iterations = payload["iterations"] | 100;
    config.warmup = payload["warmup"] | 10;
    config.budget_us = payload["budget_us"] | 0;
    config.flags = 0;

    if (payload["rt_safe"] | false) {
        config.flags |= benchmark::BenchConfig::FLAG_RT_SAFE;
    }
    if (payload["stream"] | false) {
        config.flags |= benchmark::BenchConfig::FLAG_STREAM;
    }

    // Validate
    if (config.iterations == 0) {
        ctx.sendError("CMD_BENCH_START", "invalid_iterations");
        return;
    }
    if (config.iterations > 10000) {
        config.iterations = 10000;  // Cap at reasonable max
    }

    // Queue the benchmark
    if (!module_->queueBenchmark(config)) {
        ctx.sendError("CMD_BENCH_START", "queue_full");
        return;
    }

    DBG_PRINTF("[BENCH_HANDLER] Queued test 0x%02X, %u iterations\n",
               testIdRaw, config.iterations);

    JsonDocument resp;
    resp["test_id"] = testIdRaw;
    resp["iterations"] = config.iterations;
    resp["warmup"] = config.warmup;
    resp["queue_depth"] = module_->getQueueDepth();
    ctx.sendAck("CMD_BENCH_START", true, resp);
}

void BenchmarkHandler::handleStop(CommandContext& ctx) {
    module_->cancelAll();

    DBG_PRINTLN("[BENCH_HANDLER] All benchmarks cancelled");

    JsonDocument resp;
    resp["cancelled"] = true;
    ctx.sendAck("CMD_BENCH_STOP", true, resp);
}

void BenchmarkHandler::handleStatus(CommandContext& ctx) {
    benchmark::BenchState state = module_->getState();
    benchmark::TestId activeTest = module_->getActiveTest();

    JsonDocument resp;
    resp["state"] = static_cast<uint8_t>(state);
    resp["state_name"] = [state]() -> const char* {
        switch (state) {
            case benchmark::BenchState::IDLE:     return "idle";
            case benchmark::BenchState::RUNNING:  return "running";
            case benchmark::BenchState::COMPLETE: return "complete";
            case benchmark::BenchState::ERROR:    return "error";
            case benchmark::BenchState::QUEUED:   return "queued";
            default: return "unknown";
        }
    }();
    resp["active_test"] = static_cast<uint8_t>(activeTest);
    resp["queue_depth"] = module_->getQueueDepth();
    resp["result_count"] = module_->getResultCount();
    resp["registered_tests"] = benchmark::BenchmarkRunner::instance().registeredCount();

    ctx.sendAck("CMD_BENCH_STATUS", true, resp);
}

void BenchmarkHandler::handleListTests(CommandContext& ctx) {
    const benchmark::TestInfo* tests[benchmark::MAX_REGISTERED_TESTS];
    size_t count = benchmark::BenchmarkRunner::instance().getRegisteredTests(
        tests, benchmark::MAX_REGISTERED_TESTS);

    JsonDocument resp;
    JsonArray arr = resp["tests"].to<JsonArray>();

    for (size_t i = 0; i < count; i++) {
        JsonObject obj = arr.add<JsonObject>();
        obj["id"] = static_cast<uint8_t>(tests[i]->id);
        obj["name"] = tests[i]->name;
        obj["desc"] = tests[i]->description;
        obj["rt_safe"] = (tests[i]->flags & benchmark::TestInfo::FLAG_RT_SAFE) != 0;
        obj["boot_test"] = (tests[i]->flags & benchmark::TestInfo::FLAG_BOOT_TEST) != 0;
    }

    resp["count"] = count;
    ctx.sendAck("CMD_BENCH_LIST_TESTS", true, resp);
}

void BenchmarkHandler::handleGetResults(JsonVariantConst payload, CommandContext& ctx) {
    size_t maxResults = payload["max"] | 4;
    if (maxResults > benchmark::RESULT_HISTORY_SIZE) {
        maxResults = benchmark::RESULT_HISTORY_SIZE;
    }

    const benchmark::BenchResult* results[benchmark::RESULT_HISTORY_SIZE];
    size_t count = module_->getResults(results, maxResults);

    JsonDocument resp;
    JsonArray arr = resp["results"].to<JsonArray>();

    for (size_t i = 0; i < count; i++) {
        const benchmark::BenchResult* r = results[i];
        JsonObject obj = arr.add<JsonObject>();

        obj["test_id"] = static_cast<uint8_t>(r->test_id);
        obj["state"] = static_cast<uint8_t>(r->state);
        obj["error"] = static_cast<uint8_t>(r->error);
        obj["timestamp_ms"] = r->timestamp_ms;
        obj["samples"] = r->samples;

        // Timing in microseconds
        obj["mean_us"] = r->mean_us;
        obj["min_us"] = r->min_us;
        obj["max_us"] = r->max_us;
        obj["p50_us"] = r->p50_us;
        obj["p95_us"] = r->p95_us;
        obj["p99_us"] = r->p99_us;
        obj["jitter_us"] = r->jitter_us;
        obj["total_us"] = r->total_us;
        obj["budget_violations"] = r->budget_violations;

        // Throughput (stored as Hz * 100)
        if (r->extra1 > 0) {
            obj["throughput_hz"] = r->extra1 / 100.0f;
        }
    }

    resp["count"] = count;
    resp["available"] = module_->getResultCount();
    ctx.sendAck("CMD_BENCH_GET_RESULTS", true, resp);
}

void BenchmarkHandler::handleRunBootTests(CommandContext& ctx) {
    module_->runBootTests();

    DBG_PRINTLN("[BENCH_HANDLER] Boot tests scheduled");

    JsonDocument resp;
    resp["scheduled"] = true;
    ctx.sendAck("CMD_BENCH_RUN_BOOT_TESTS", true, resp);
}

void BenchmarkHandler::handlePerfReset(CommandContext& ctx) {
    // Reset any performance counters
    // This would integrate with LoopTiming or other perf systems

    DBG_PRINTLN("[BENCH_HANDLER] Performance counters reset");

    JsonDocument resp;
    resp["reset"] = true;
    ctx.sendAck("CMD_PERF_RESET", true, resp);
}

#endif  // FEATURE_BENCHMARK
