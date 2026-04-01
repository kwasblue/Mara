# schema/commands/_benchmark.py
"""Benchmark command definitions for MCU performance testing."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


BENCHMARK_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_BENCH_START": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Start a benchmark test on the MCU.",
        payload={
            "test_id": FieldDef(
                type="int",
                required=True,
                description="Test ID to run (see CMD_BENCH_LIST_TESTS for available tests)",
                minimum=0,
                maximum=255,
            ),
            "iterations": FieldDef(
                type="int",
                required=False,
                default=100,
                description="Number of test iterations",
                minimum=1,
                maximum=10000,
            ),
            "warmup": FieldDef(
                type="int",
                required=False,
                default=10,
                description="Number of warmup iterations (not timed)",
                minimum=0,
                maximum=1000,
            ),
            "budget_us": FieldDef(
                type="int",
                required=False,
                default=0,
                description="Max time budget per iteration in microseconds (0 = unlimited)",
                minimum=0,
                units="us",
            ),
            "rt_safe": FieldDef(
                type="bool",
                required=False,
                default=False,
                description="Run in real-time safe context",
            ),
            "stream": FieldDef(
                type="bool",
                required=False,
                default=False,
                description="Stream results as they complete",
            ),
        },
        response={
            "test_id": FieldDef(type="int", description="Queued test ID"),
            "iterations": FieldDef(type="int", description="Actual iterations"),
            "warmup": FieldDef(type="int", description="Warmup iterations"),
            "queue_depth": FieldDef(type="int", description="Current queue depth"),
        },
    ),
    "CMD_BENCH_STOP": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Cancel all running and queued benchmarks.",
        payload={},
        response={
            "cancelled": FieldDef(type="bool", description="True if cancellation succeeded"),
        },
    ),
    "CMD_BENCH_STATUS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get current benchmark system status.",
        payload={},
        response={
            "state": FieldDef(
                type="int",
                description="Current state (0=idle, 1=running, 2=complete, 3=error, 4=queued)",
            ),
            "state_name": FieldDef(type="string", description="Human-readable state name"),
            "active_test": FieldDef(type="int", description="Currently running test ID (0 if none)"),
            "queue_depth": FieldDef(type="int", description="Number of queued benchmarks"),
            "result_count": FieldDef(type="int", description="Number of available results"),
            "registered_tests": FieldDef(type="int", description="Number of registered tests"),
        },
    ),
    "CMD_BENCH_LIST_TESTS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="List all available benchmark tests.",
        payload={},
        response={
            "tests": FieldDef(
                type="array",
                description="Array of test definitions",
                items={
                    "type": "object",
                    "properties": {
                        "id": FieldDef(type="int", description="Test ID"),
                        "name": FieldDef(type="string", description="Test name"),
                        "desc": FieldDef(type="string", description="Test description"),
                        "rt_safe": FieldDef(type="bool", description="Can run in RT context"),
                        "boot_test": FieldDef(type="bool", description="Runs at boot"),
                    },
                },
            ),
            "count": FieldDef(type="int", description="Number of tests"),
        },
    ),
    "CMD_BENCH_GET_RESULTS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get benchmark result history.",
        payload={
            "max": FieldDef(
                type="int",
                required=False,
                default=4,
                description="Maximum number of results to return",
                minimum=1,
                maximum=8,
            ),
        },
        response={
            "results": FieldDef(
                type="array",
                description="Array of benchmark results",
                items={
                    "type": "object",
                    "properties": {
                        "test_id": FieldDef(type="int", description="Test ID"),
                        "state": FieldDef(type="int", description="Result state"),
                        "error": FieldDef(type="int", description="Error code"),
                        "timestamp_ms": FieldDef(type="int", description="Completion time"),
                        "samples": FieldDef(type="int", description="Number of samples"),
                        "mean_us": FieldDef(type="int", description="Mean time in us"),
                        "min_us": FieldDef(type="int", description="Min time in us"),
                        "max_us": FieldDef(type="int", description="Max time in us"),
                        "p50_us": FieldDef(type="int", description="50th percentile in us"),
                        "p95_us": FieldDef(type="int", description="95th percentile in us"),
                        "p99_us": FieldDef(type="int", description="99th percentile in us"),
                        "jitter_us": FieldDef(type="int", description="Jitter (stddev) in us"),
                        "total_us": FieldDef(type="int", description="Total test time in us"),
                        "budget_violations": FieldDef(type="int", description="Budget exceeded count"),
                        "throughput_hz": FieldDef(type="float", description="Throughput in Hz"),
                    },
                },
            ),
            "count": FieldDef(type="int", description="Number of results returned"),
            "available": FieldDef(type="int", description="Total results available"),
        },
    ),
    "CMD_BENCH_RUN_BOOT_TESTS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Manually trigger boot-time benchmark tests.",
        payload={},
        response={
            "scheduled": FieldDef(type="bool", description="True if boot tests scheduled"),
        },
    ),
    "CMD_PERF_RESET": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Reset MCU performance counters and statistics.",
        payload={},
        response={
            "reset": FieldDef(type="bool", description="True if counters reset"),
        },
    ),
}


# Legacy dict export for backward compatibility
BENCHMARK_COMMANDS: dict[str, dict] = export_command_dicts(BENCHMARK_COMMAND_OBJECTS)
