# mara_host/benchmarks/serialization/compare.py
"""
JSON vs Binary serialization comparison benchmark.

Category: Micro + Integration
Measures: Serialization cost and wire latency difference between JSON and binary.

Usage:
    python -m mara_host.benchmarks.serialization.compare --iterations 1000
    python -m mara_host.benchmarks.serialization.compare --port /dev/tty.usbserial --iterations 500
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import json
import struct
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mara_host.benchmarks.core import (
    BenchmarkEnvironment,
    BenchmarkReport,
    BenchmarkResult,
    make_result,
    print_header,
    print_section,
    print_comparison,
)


@dataclass
class SerializationComparison:
    """Comparison results between JSON and binary."""

    # Encoding benchmarks (micro)
    json_encode_us: float
    binary_encode_us: float
    encode_speedup: float

    # Size comparison
    json_size_bytes: int
    binary_size_bytes: int
    size_reduction_pct: float

    # Wire RTT (if hardware available)
    json_rtt_ms: Optional[float] = None
    binary_rtt_ms: Optional[float] = None
    rtt_speedup: Optional[float] = None


def benchmark_encoding_comparison(
    iterations: int = 10000,
) -> tuple[SerializationComparison, Dict[str, BenchmarkResult]]:
    """
    Compare JSON vs binary encoding (micro benchmark, no hardware).

    Returns:
        (SerializationComparison, detailed_results)
    """
    # Test payload: velocity command
    json_payload = {
        "kind": "cmd",
        "type": "CMD_SET_VEL",
        "seq": 123,
        "vx": 0.5,
        "omega": 0.1,
    }

    # JSON encoding
    json_encoded = json.dumps(json_payload, separators=(",", ":")).encode("utf-8")
    json_size = len(json_encoded)

    gc.disable()
    json_times: List[float] = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        _ = json.dumps(json_payload, separators=(",", ":")).encode("utf-8")
        json_times.append((time.perf_counter_ns() - start) / 1000.0)  # microseconds
    gc.enable()

    # Binary encoding
    CMD_SET_VEL_BIN = 0x10
    binary_encoded = struct.pack("<BHff", CMD_SET_VEL_BIN, 123, 0.5, 0.1)
    binary_size = len(binary_encoded)

    gc.disable()
    binary_times: List[float] = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        _ = struct.pack("<BHff", CMD_SET_VEL_BIN, 123, 0.5, 0.1)
        binary_times.append((time.perf_counter_ns() - start) / 1000.0)
    gc.enable()

    # Calculate averages
    import statistics

    json_avg_us = statistics.mean(json_times)
    binary_avg_us = statistics.mean(binary_times)

    comparison = SerializationComparison(
        json_encode_us=json_avg_us,
        binary_encode_us=binary_avg_us,
        encode_speedup=json_avg_us / binary_avg_us if binary_avg_us > 0 else 0,
        json_size_bytes=json_size,
        binary_size_bytes=binary_size,
        size_reduction_pct=(1 - binary_size / json_size) * 100 if json_size > 0 else 0,
    )

    # Create detailed results
    json_result = make_result(
        name="json_encode_velocity",
        times_ms=[t / 1000 for t in json_times],  # Convert us to ms
        metadata={"size_bytes": json_size},
    )
    binary_result = make_result(
        name="binary_encode_velocity",
        times_ms=[t / 1000 for t in binary_times],
        metadata={"size_bytes": binary_size},
    )

    return comparison, {
        "json_encode": json_result,
        "binary_encode": binary_result,
    }


async def benchmark_wire_comparison(
    port: Optional[str] = None,
    tcp_host: Optional[str] = None,
    tcp_port: int = 3333,
    iterations: int = 100,
) -> tuple[Optional[float], Optional[float]]:
    """
    Compare JSON vs binary wire RTT (requires hardware).

    Returns:
        (json_rtt_ms, binary_rtt_ms)
    """
    from mara_host.core.event_bus import EventBus
    from mara_host.command.client import MaraClient

    bus = EventBus()

    # Create transport
    if port:
        from mara_host.transport.serial_transport import SerialTransport

        transport = SerialTransport(port=port, baudrate=115200)
    elif tcp_host:
        from mara_host.transport.tcp_transport import AsyncTcpTransport

        transport = AsyncTcpTransport(host=tcp_host, port=tcp_port)
    else:
        return None, None

    client = MaraClient(transport=transport, bus=bus)

    try:
        await client.start()

        # Warmup
        for _ in range(10):
            await client.send_reliable("CMD_HEARTBEAT", {}, wait_for_ack=True, timeout_s=2.0)
            await asyncio.sleep(0.05)

        # JSON RTT measurement
        json_times: List[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            await client.send_reliable(
                "CMD_SET_VEL",
                {"vx": 0.0, "omega": 0.0},
                wait_for_ack=True,
                timeout_s=2.0,
            )
            json_times.append((time.perf_counter() - start) * 1000)
            await asyncio.sleep(0.02)

        # Binary RTT measurement (if client supports it)
        binary_times: List[float] = []
        if hasattr(client, "send_binary_cmd"):
            for _ in range(iterations):
                start = time.perf_counter()
                await client.send_binary_cmd(
                    "CMD_SET_VEL",
                    {"vx": 0.0, "omega": 0.0},
                )
                binary_times.append((time.perf_counter() - start) * 1000)
                await asyncio.sleep(0.02)
        else:
            # Fallback: use reliable with binary flag if available
            try:
                for _ in range(iterations):
                    start = time.perf_counter()
                    # Try binary path if available
                    if hasattr(client.commander, "send_fire_and_forget"):
                        await client.commander.send_fire_and_forget(
                            "CMD_SET_VEL",
                            {"vx": 0.0, "omega": 0.0},
                            binary=True,
                        )
                    binary_times.append((time.perf_counter() - start) * 1000)
                    await asyncio.sleep(0.02)
            except Exception:
                binary_times = json_times  # Fallback to same as JSON

        import statistics

        json_rtt = statistics.mean(json_times) if json_times else None
        binary_rtt = statistics.mean(binary_times) if binary_times else None

        return json_rtt, binary_rtt

    finally:
        await client.stop()


def run_benchmark(
    iterations: int = 1000,
    port: Optional[str] = None,
    tcp_host: Optional[str] = None,
    tcp_port: int = 3333,
    save_report: bool = True,
) -> SerializationComparison:
    """
    Run full serialization comparison benchmark.

    Args:
        iterations: Number of iterations for micro benchmarks
        port: Serial port for wire test (optional)
        tcp_host: TCP host for wire test (optional)
        tcp_port: TCP port (default 3333)
        save_report: Whether to save JSON report
    """
    print_header("JSON vs Binary Serialization Comparison")

    # Micro benchmark (always runs)
    print_section("Encoding Performance (Micro)")
    comparison, results = benchmark_encoding_comparison(iterations)

    print(f"  JSON encode:   {comparison.json_encode_us:.3f}μs, {comparison.json_size_bytes} bytes")
    print(f"  Binary encode: {comparison.binary_encode_us:.3f}μs, {comparison.binary_size_bytes} bytes")
    print(f"  Speedup:       {comparison.encode_speedup:.1f}x faster")
    print(f"  Size savings:  {comparison.size_reduction_pct:.0f}%")

    # Wire benchmark (requires hardware)
    if port or tcp_host:
        print_section("Wire RTT Comparison (Integration)")
        wire_iterations = min(iterations, 100)  # Limit for hardware test

        json_rtt, binary_rtt = asyncio.run(
            benchmark_wire_comparison(port, tcp_host, tcp_port, wire_iterations)
        )

        if json_rtt and binary_rtt:
            comparison.json_rtt_ms = json_rtt
            comparison.binary_rtt_ms = binary_rtt
            comparison.rtt_speedup = json_rtt / binary_rtt if binary_rtt > 0 else None

            print(f"  JSON RTT:   {json_rtt:.2f}ms")
            print(f"  Binary RTT: {binary_rtt:.2f}ms")
            if comparison.rtt_speedup:
                print(f"  RTT Speedup: {comparison.rtt_speedup:.2f}x")

    # Summary
    print_section("Summary")
    print(f"  Encoding speedup: {comparison.encode_speedup:.1f}x")
    print(f"  Wire size reduction: {comparison.size_reduction_pct:.0f}%")
    if comparison.rtt_speedup:
        print(f"  Wire RTT speedup: {comparison.rtt_speedup:.2f}x")

    # Save report
    if save_report:
        env = BenchmarkEnvironment.capture(
            transport="serial" if port else ("tcp" if tcp_host else "none"),
            port_or_host=port or f"{tcp_host}:{tcp_port}" if tcp_host else "localhost",
            baud_rate=115200 if port else None,
            protocol="comparison",
        )

        # Create combined result
        combined_result = make_result(
            name="serialization_comparison",
            times_ms=[comparison.json_encode_us / 1000],  # Use JSON as baseline
            metadata={
                "json_encode_us": comparison.json_encode_us,
                "binary_encode_us": comparison.binary_encode_us,
                "encode_speedup": comparison.encode_speedup,
                "json_size_bytes": comparison.json_size_bytes,
                "binary_size_bytes": comparison.binary_size_bytes,
                "size_reduction_pct": comparison.size_reduction_pct,
                "json_rtt_ms": comparison.json_rtt_ms,
                "binary_rtt_ms": comparison.binary_rtt_ms,
                "rtt_speedup": comparison.rtt_speedup,
            },
        )

        report = BenchmarkReport(
            benchmark="serialization_compare",
            environment=env,
            results=combined_result,
        )
        filepath = report.save()
        print(f"\n  Report saved: {filepath}")

    return comparison


def main() -> None:
    parser = argparse.ArgumentParser(description="JSON vs Binary Comparison Benchmark")
    parser.add_argument("--iterations", "-n", type=int, default=1000)
    parser.add_argument("--port", "-p", help="Serial port for wire test")
    parser.add_argument("--tcp", help="TCP host:port for wire test")
    parser.add_argument("--no-save", action="store_true", help="Don't save report")

    args = parser.parse_args()

    tcp_host = None
    tcp_port = 3333
    if args.tcp:
        if ":" in args.tcp:
            tcp_host, tcp_port_str = args.tcp.rsplit(":", 1)
            tcp_port = int(tcp_port_str)
        else:
            tcp_host = args.tcp

    run_benchmark(
        iterations=args.iterations,
        port=args.port,
        tcp_host=tcp_host,
        tcp_port=tcp_port,
        save_report=not args.no_save,
    )


if __name__ == "__main__":
    main()
