# schema/telemetry/_benchmark.py
"""Benchmark telemetry section definition (TELEM_BENCHMARK 0x13)."""

from __future__ import annotations

import struct
from typing import Any, Dict, Optional

from .core import TelemetrySectionDef, FieldDef


def parse_benchmark_section(body: bytes, ts_ms: int) -> Optional[Dict[str, Any]]:
    """
    Custom parser for TELEM_BENCHMARK section.

    Format:
        Header (4 bytes):
            bench_state(u8)     - Current state (0=idle, 1=running, 2=complete, 3=error, 4=queued)
            active_test(u8)     - Currently running test ID
            queue_depth(u8)     - Number of queued benchmarks
            result_count(u8)    - Number of results available

        Optional BenchResult (56 bytes):
            If result_count > 0, the latest result is included.
    """
    if len(body) < 4:
        return None

    result: Dict[str, Any] = {"ts_ms": ts_ms}

    # Parse header
    result["bench_state"] = body[0]
    result["active_test"] = body[1]
    result["queue_depth"] = body[2]
    result["result_count"] = body[3]

    # State name mapping
    state_names = {
        0: "idle",
        1: "running",
        2: "complete",
        3: "error",
        4: "queued",
    }
    result["state_name"] = state_names.get(body[0], "unknown")

    # Parse BenchResult if present (56 bytes)
    if len(body) >= 60:  # 4 header + 56 result
        result_data = body[4:60]

        # BenchResult structure (little-endian, packed):
        # Header (8 bytes):
        #   test_id(u8), state(u8), error(u8), reserved(u8), timestamp_ms(u32)
        # Timing stats (36 bytes):
        #   mean_us(u32), min_us(u32), max_us(u32), p50_us(u32), p95_us(u32), p99_us(u32),
        #   jitter_us(u32), total_us(u32), samples(u16), budget_violations(u16)
        # Extra (12 bytes):
        #   extra1(u32), extra2(u32), extra3(u32)

        fmt = "<BBBBI IIIIIIII HH III"
        if len(result_data) >= struct.calcsize(fmt):
            unpacked = struct.unpack(fmt, result_data[:struct.calcsize(fmt)])

            result["latest"] = {
                "test_id": unpacked[0],
                "state": unpacked[1],
                "error": unpacked[2],
                "timestamp_ms": unpacked[4],
                "mean_us": unpacked[5],
                "min_us": unpacked[6],
                "max_us": unpacked[7],
                "p50_us": unpacked[8],
                "p95_us": unpacked[9],
                "p99_us": unpacked[10],
                "jitter_us": unpacked[11],
                "total_us": unpacked[12],
                "samples": unpacked[13],
                "budget_violations": unpacked[14],
                "throughput_hz": unpacked[15] / 100.0 if unpacked[15] > 0 else None,
                "extra2": unpacked[16],
                "extra3": unpacked[17],
            }

            # Convert microseconds to milliseconds for convenience
            latest = result["latest"]
            result["latest"]["mean_ms"] = latest["mean_us"] / 1000.0
            result["latest"]["p99_ms"] = latest["p99_us"] / 1000.0

    return result


SECTION = TelemetrySectionDef(
    name="TELEM_BENCHMARK",
    section_id=0x13,
    description="Benchmark system state and latest results",
    variable_length=True,
    custom_parser=parse_benchmark_section,
    fields=(
        # These are just for documentation - actual parsing uses custom_parser
        FieldDef.uint8("bench_state", description="Current state"),
        FieldDef.uint8("active_test", description="Running test ID"),
        FieldDef.uint8("queue_depth", description="Queued benchmarks"),
        FieldDef.uint8("result_count", description="Available results"),
    ),
)
