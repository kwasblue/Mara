# mara_host/benchmarks/serialization/binary_bench.py
"""
Binary encoding benchmark - measures binary serialization performance.

Category: Micro
Measures: Binary encoding time for various command payloads using struct.

Usage:
    python -m mara_host.benchmarks.serialization.binary_bench --iterations 10000
"""

from __future__ import annotations

import argparse
import gc
import struct
import time
from typing import Any, Dict, List, Optional

from mara_host.benchmarks.core import (
    BenchmarkResult,
    make_result,
    print_header,
)


# Command IDs (example values - would come from schema in real implementation)
CMD_IDS = {
    "CMD_HEARTBEAT": 0x00,
    "CMD_SET_VEL": 0x10,
    "CMD_SERVO_MOVE": 0x20,
    "CMD_MOTOR_SET": 0x30,
}

# Struct formats for binary encoding
STRUCT_FORMATS = {
    "minimal": "<BH",  # cmd_id + seq
    "velocity": "<BHff",  # cmd_id + seq + vx + omega
    "servo": "<BHBHh",  # cmd_id + seq + channel + position + speed
}


def encode_binary_minimal(seq: int) -> bytes:
    """Encode minimal command (NOP)."""
    return struct.pack("<BH", CMD_IDS["CMD_HEARTBEAT"], seq)


def encode_binary_velocity(seq: int, vx: float, omega: float) -> bytes:
    """Encode velocity command."""
    return struct.pack("<BHff", CMD_IDS["CMD_SET_VEL"], seq, vx, omega)


def encode_binary_servo(
    seq: int, channel: int, position: int, speed: int
) -> bytes:
    """Encode servo command."""
    return struct.pack(
        "<BHBHh", CMD_IDS["CMD_SERVO_MOVE"], seq, channel, position, speed
    )


def benchmark_binary_encode(
    encoder_name: str,
    iterations: int = 10000,
    warmup: int = 100,
) -> tuple[BenchmarkResult, int]:
    """
    Benchmark binary encoding.

    Returns:
        (BenchmarkResult, payload_size_bytes)
    """
    # Select encoder
    if encoder_name == "minimal":
        encode_func = lambda: encode_binary_minimal(123)
    elif encoder_name == "velocity":
        encode_func = lambda: encode_binary_velocity(123, 0.5, 0.1)
    elif encoder_name == "servo":
        encode_func = lambda: encode_binary_servo(123, 0, 1500, 100)
    else:
        encode_func = lambda: encode_binary_velocity(123, 0.5, 0.1)

    # Get size
    encoded = encode_func()
    size_bytes = len(encoded)

    # Warmup
    for _ in range(warmup):
        encode_func()

    # Benchmark
    gc.disable()
    times_ms: List[float] = []
    try:
        for _ in range(iterations):
            start = time.perf_counter_ns()
            _ = encode_func()
            elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
            times_ms.append(elapsed_ms)
    finally:
        gc.enable()

    result = make_result(
        name=f"binary_encode_{encoder_name}",
        times_ms=times_ms,
        metadata={"size_bytes": size_bytes},
    )

    return result, size_bytes


def benchmark_binary_decode(
    encoder_name: str,
    iterations: int = 10000,
    warmup: int = 100,
) -> BenchmarkResult:
    """Benchmark binary decoding."""
    # Select format and create encoded data
    if encoder_name == "minimal":
        fmt = "<BH"
        encoded = encode_binary_minimal(123)
    elif encoder_name == "velocity":
        fmt = "<BHff"
        encoded = encode_binary_velocity(123, 0.5, 0.1)
    elif encoder_name == "servo":
        fmt = "<BHBHh"
        encoded = encode_binary_servo(123, 0, 1500, 100)
    else:
        fmt = "<BHff"
        encoded = encode_binary_velocity(123, 0.5, 0.1)

    # Pre-compile struct for consistent measurement
    s = struct.Struct(fmt)
    unpack = s.unpack

    # Warmup
    for _ in range(warmup):
        unpack(encoded)

    # Benchmark
    gc.disable()
    times_ms: List[float] = []
    try:
        for _ in range(iterations):
            start = time.perf_counter_ns()
            _ = unpack(encoded)
            elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
            times_ms.append(elapsed_ms)
    finally:
        gc.enable()

    return make_result(
        name=f"binary_decode_{encoder_name}",
        times_ms=times_ms,
        metadata={"size_bytes": len(encoded)},
    )


def run_benchmark(
    iterations: int = 10000,
    payload_name: str = "velocity",
) -> Dict[str, BenchmarkResult]:
    """Run binary encoding benchmarks."""
    print_header("Binary Serialization Benchmark")

    results = {}

    if payload_name == "all":
        payloads = ["minimal", "velocity", "servo"]
    else:
        payloads = [payload_name]

    for name in payloads:
        print(f"\n  Payload: {name}")

        # Encode benchmark
        encode_result, size = benchmark_binary_encode(name, iterations)
        encode_us = encode_result.mean_ms * 1000
        print(f"    Encode: {encode_us:.3f}μs, {size} bytes")

        # Decode benchmark
        decode_result = benchmark_binary_decode(name, iterations)
        decode_us = decode_result.mean_ms * 1000
        print(f"    Decode: {decode_us:.3f}μs")

        results[f"binary_encode_{name}"] = encode_result
        results[f"binary_decode_{name}"] = decode_result

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Binary Serialization Benchmark")
    parser.add_argument("--iterations", "-n", type=int, default=10000)
    parser.add_argument(
        "--payload",
        "-p",
        choices=["minimal", "velocity", "servo", "all"],
        default="velocity",
    )

    args = parser.parse_args()
    run_benchmark(iterations=args.iterations, payload_name=args.payload)


if __name__ == "__main__":
    main()
