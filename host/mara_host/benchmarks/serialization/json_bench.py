# mara_host/benchmarks/serialization/json_bench.py
"""
JSON encoding benchmark - measures pure JSON serialization performance.

Category: Micro
Measures: JSON encoding time for various command payloads.

Usage:
    python -m mara_host.benchmarks.serialization.json_bench --iterations 10000
"""

from __future__ import annotations

import argparse
import gc
import json
import time
from typing import Any, Dict, List

from mara_host.benchmarks.core import (
    BenchmarkResult,
    make_result,
    print_header,
    print_result,
    timed_loop,
)


# Test payloads of varying complexity
TEST_PAYLOADS = {
    "minimal": {
        "kind": "cmd",
        "type": "CMD_HEARTBEAT",
        "seq": 123,
    },
    "velocity": {
        "kind": "cmd",
        "type": "CMD_SET_VEL",
        "seq": 123,
        "vx": 0.5,
        "omega": 0.1,
    },
    "servo": {
        "kind": "cmd",
        "type": "CMD_SERVO_MOVE",
        "seq": 123,
        "channel": 0,
        "position": 1500,
        "speed": 100,
    },
    "motor_multi": {
        "kind": "cmd",
        "type": "CMD_MOTOR_SET",
        "seq": 123,
        "motors": [
            {"id": 0, "speed": 100, "direction": 1},
            {"id": 1, "speed": 100, "direction": 0},
            {"id": 2, "speed": 50, "direction": 1},
            {"id": 3, "speed": 50, "direction": 0},
        ],
    },
}

# JSON separators for compact encoding (no whitespace)
_JSON_SEPARATORS = (",", ":")


def benchmark_json_encode(
    payload: Dict[str, Any],
    iterations: int = 10000,
    warmup: int = 100,
) -> tuple[BenchmarkResult, int]:
    """
    Benchmark JSON encoding.

    Returns:
        (BenchmarkResult, payload_size_bytes)
    """
    # Pre-serialize once to get size
    encoded = json.dumps(payload, separators=_JSON_SEPARATORS).encode("utf-8")
    size_bytes = len(encoded)

    # Warmup
    for _ in range(warmup):
        json.dumps(payload, separators=_JSON_SEPARATORS).encode("utf-8")

    # Benchmark
    gc.disable()
    times_ms: List[float] = []
    try:
        for _ in range(iterations):
            start = time.perf_counter_ns()
            _ = json.dumps(payload, separators=_JSON_SEPARATORS).encode("utf-8")
            elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
            times_ms.append(elapsed_ms)
    finally:
        gc.enable()

    result = make_result(
        name="json_encode",
        times_ms=times_ms,
        metadata={"size_bytes": size_bytes},
    )

    return result, size_bytes


def benchmark_json_decode(
    payload: Dict[str, Any],
    iterations: int = 10000,
    warmup: int = 100,
) -> BenchmarkResult:
    """Benchmark JSON decoding."""
    encoded = json.dumps(payload, separators=_JSON_SEPARATORS).encode("utf-8")

    # Warmup
    for _ in range(warmup):
        json.loads(encoded)

    # Benchmark
    gc.disable()
    times_ms: List[float] = []
    try:
        for _ in range(iterations):
            start = time.perf_counter_ns()
            _ = json.loads(encoded)
            elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
            times_ms.append(elapsed_ms)
    finally:
        gc.enable()

    return make_result(
        name="json_decode",
        times_ms=times_ms,
        metadata={"size_bytes": len(encoded)},
    )


def run_benchmark(
    iterations: int = 10000,
    payload_name: str = "velocity",
) -> Dict[str, BenchmarkResult]:
    """Run JSON encoding benchmarks."""
    print_header("JSON Serialization Benchmark")

    results = {}

    if payload_name == "all":
        payloads = TEST_PAYLOADS
    else:
        payloads = {payload_name: TEST_PAYLOADS.get(payload_name, TEST_PAYLOADS["velocity"])}

    for name, payload in payloads.items():
        print(f"\n  Payload: {name}")

        # Encode benchmark
        encode_result, size = benchmark_json_encode(payload, iterations)
        encode_us = encode_result.mean_ms * 1000
        print(f"    Encode: {encode_us:.3f}μs, {size} bytes")

        # Decode benchmark
        decode_result = benchmark_json_decode(payload, iterations)
        decode_us = decode_result.mean_ms * 1000
        print(f"    Decode: {decode_us:.3f}μs")

        results[f"json_encode_{name}"] = encode_result
        results[f"json_decode_{name}"] = decode_result

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="JSON Serialization Benchmark")
    parser.add_argument("--iterations", "-n", type=int, default=10000)
    parser.add_argument(
        "--payload",
        "-p",
        choices=["minimal", "velocity", "servo", "motor_multi", "all"],
        default="velocity",
    )

    args = parser.parse_args()
    run_benchmark(iterations=args.iterations, payload_name=args.payload)


if __name__ == "__main__":
    main()
