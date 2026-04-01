// include/command/handlers/BenchmarkHandler.h
// Handles benchmark commands (CMD_BENCH_*)

#pragma once

#ifdef FEATURE_BENCHMARK

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "benchmark/BenchmarkModule.h"

/**
 * Handler for benchmark commands.
 *
 * Commands:
 * - CMD_BENCH_START - Start a benchmark
 * - CMD_BENCH_STOP - Cancel running/queued benchmarks
 * - CMD_BENCH_STATUS - Get current state and queue depth
 * - CMD_BENCH_LIST_TESTS - List available tests
 * - CMD_BENCH_GET_RESULTS - Get result history
 * - CMD_BENCH_RUN_BOOT_TESTS - Trigger boot tests manually
 * - CMD_PERF_RESET - Reset performance counters
 */
class BenchmarkHandler : public ICommandHandler {
public:
    explicit BenchmarkHandler(benchmark::BenchmarkModule& module)
        : module_(module) {}

    const char* name() const override { return "BenchmarkHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::BENCH_START:
            case CmdType::BENCH_STOP:
            case CmdType::BENCH_STATUS:
            case CmdType::BENCH_LIST_TESTS:
            case CmdType::BENCH_GET_RESULTS:
            case CmdType::BENCH_RUN_BOOT_TESTS:
            case CmdType::PERF_RESET:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::BENCH_START:         handleStart(payload, ctx); break;
            case CmdType::BENCH_STOP:          handleStop(ctx); break;
            case CmdType::BENCH_STATUS:        handleStatus(ctx); break;
            case CmdType::BENCH_LIST_TESTS:    handleListTests(ctx); break;
            case CmdType::BENCH_GET_RESULTS:   handleGetResults(payload, ctx); break;
            case CmdType::BENCH_RUN_BOOT_TESTS: handleRunBootTests(ctx); break;
            case CmdType::PERF_RESET:          handlePerfReset(ctx); break;
            default: break;
        }
    }

private:
    benchmark::BenchmarkModule& module_;

    // Implemented in BenchmarkHandler.cpp
    void handleStart(JsonVariantConst payload, CommandContext& ctx);
    void handleStop(CommandContext& ctx);
    void handleStatus(CommandContext& ctx);
    void handleListTests(CommandContext& ctx);
    void handleGetResults(JsonVariantConst payload, CommandContext& ctx);
    void handleRunBootTests(CommandContext& ctx);
    void handlePerfReset(CommandContext& ctx);
};

#endif  // FEATURE_BENCHMARK
