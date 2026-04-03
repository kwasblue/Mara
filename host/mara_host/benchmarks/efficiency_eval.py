#!/usr/bin/env python3
"""
Efficiency Evaluator for MARA Host

Measures key performance metrics to evaluate optimization progress:
1. Import time - how long to load mara_host
2. Velocity command latency - time per set_velocity call
3. Wire size - bytes sent per command
4. Event bus overhead - handler dispatch time
5. Transport layer - executor overhead

Run before and after optimizations to compare.

Usage:
    # Quick eval (no hardware required)
    python -m mara_host.benchmarks.efficiency_eval

    # Full eval with hardware
    python -m mara_host.benchmarks.efficiency_eval --port /dev/ttyUSB0
"""

import argparse
import asyncio
import gc
import json
import struct
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import statistics


@dataclass
class BenchmarkResult:
    """Results from a single benchmark."""
    name: str
    iterations: int
    total_time_ms: float
    per_call_us: float
    min_us: float = 0.0
    max_us: float = 0.0
    stddev_us: float = 0.0
    extra: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return (
            f"{self.name}:\n"
            f"  iterations: {self.iterations}\n"
            f"  total: {self.total_time_ms:.2f}ms\n"
            f"  per call: {self.per_call_us:.2f}μs\n"
            f"  min/max: {self.min_us:.2f}/{self.max_us:.2f}μs\n"
            f"  stddev: {self.stddev_us:.2f}μs"
        )


class EfficiencyEvaluator:
    """Evaluates mara_host efficiency metrics."""

    def __init__(self, port: Optional[str] = None):
        self.port = port
        self.results: List[BenchmarkResult] = []

    def run_all(self) -> None:
        """Run all benchmarks."""
        print("=" * 60)
        print("MARA Host Efficiency Evaluation")
        print("=" * 60)
        print()

        # Always run these (no hardware needed)
        self.bench_import_time()
        self.bench_json_vs_binary_encode()
        self.bench_event_bus()
        self.bench_protocol_encode()
        self.bench_dict_operations()

        # Hardware-required benchmarks
        if self.port:
            asyncio.run(self.bench_velocity_latency())
            asyncio.run(self.bench_transport_overhead())
        else:
            print("\n[SKIPPED] Hardware benchmarks (no --port specified)")

        self.print_summary()

    def bench_import_time(self) -> None:
        """Measure import time for mara_host."""
        print("\n--- Import Time Benchmark ---")

        # Fresh import measurement (requires subprocess for accuracy)
        import subprocess
        code = """
import time
gc_start = time.perf_counter()
import gc
gc.disable()
start = time.perf_counter()
from mara_host import Robot
elapsed = time.perf_counter() - start
print(f"{elapsed * 1000:.2f}")
"""
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(Path(__file__).parent.parent.parent),
            )
            import_ms = float(result.stdout.strip())
        except Exception as e:
            print(f"  [ERROR] Could not measure import time: {e}")
            import_ms = -1

        # Measure submodule imports
        submodules = [
            "mara_host.core.event_bus",
            "mara_host.core.protocol",
            "mara_host.command.client",
            "mara_host.services.control.motion_service",
        ]

        print(f"  mara_host.Robot: {import_ms:.2f}ms")

        self.results.append(BenchmarkResult(
            name="import_robot",
            iterations=1,
            total_time_ms=import_ms,
            per_call_us=import_ms * 1000,
        ))

    def bench_json_vs_binary_encode(self) -> None:
        """Compare JSON vs binary encoding for velocity command."""
        print("\n--- JSON vs Binary Encoding ---")

        iterations = 10000
        vx, omega = 0.5, 0.1

        # JSON encoding
        gc.disable()
        times_json = []
        for _ in range(iterations):
            start = time.perf_counter()
            cmd = {"kind": "cmd", "type": "CMD_SET_VEL", "seq": 123, "vx": vx, "omega": omega}
            data = json.dumps(cmd, separators=(",", ":")).encode("utf-8")
            times_json.append(time.perf_counter() - start)
        gc.enable()

        json_size = len(data)
        json_us = statistics.mean(times_json) * 1e6

        # Binary encoding
        CMD_SET_VEL_BIN = 0x10  # Example command ID
        gc.disable()
        times_bin = []
        for _ in range(iterations):
            start = time.perf_counter()
            data = struct.pack("<Bff", CMD_SET_VEL_BIN, vx, omega)
            times_bin.append(time.perf_counter() - start)
        gc.enable()

        bin_size = len(data)
        bin_us = statistics.mean(times_bin) * 1e6

        print(f"  JSON encode: {json_us:.3f}μs, {json_size} bytes")
        print(f"  Binary encode: {bin_us:.3f}μs, {bin_size} bytes")
        print(f"  Speedup: {json_us / bin_us:.1f}x faster")
        print(f"  Size reduction: {(1 - bin_size / json_size) * 100:.0f}%")

        self.results.append(BenchmarkResult(
            name="json_encode_velocity",
            iterations=iterations,
            total_time_ms=sum(times_json) * 1000,
            per_call_us=json_us,
            min_us=min(times_json) * 1e6,
            max_us=max(times_json) * 1e6,
            stddev_us=statistics.stdev(times_json) * 1e6,
            extra={"bytes": json_size},
        ))

        self.results.append(BenchmarkResult(
            name="binary_encode_velocity",
            iterations=iterations,
            total_time_ms=sum(times_bin) * 1000,
            per_call_us=bin_us,
            min_us=min(times_bin) * 1e6,
            max_us=max(times_bin) * 1e6,
            stddev_us=statistics.stdev(times_bin) * 1e6,
            extra={"bytes": bin_size},
        ))

    def bench_event_bus(self) -> None:
        """Measure event bus publish overhead."""
        print("\n--- Event Bus Overhead ---")

        from mara_host.core.event_bus import EventBus

        bus = EventBus()
        iterations = 10000
        data = {"vx": 0.5, "omega": 0.1}

        # No subscribers
        gc.disable()
        times_empty = []
        for _ in range(iterations):
            start = time.perf_counter()
            bus.publish("test.topic", data)
            times_empty.append(time.perf_counter() - start)
        gc.enable()

        empty_us = statistics.mean(times_empty) * 1e6

        # With 1 subscriber
        handler_calls = [0]
        def handler(d):
            handler_calls[0] += 1

        bus.subscribe("test.topic", handler)

        gc.disable()
        times_1sub = []
        for _ in range(iterations):
            start = time.perf_counter()
            bus.publish("test.topic", data)
            times_1sub.append(time.perf_counter() - start)
        gc.enable()

        sub1_us = statistics.mean(times_1sub) * 1e6

        # With 5 subscribers
        for _ in range(4):
            bus.subscribe("test.topic", handler)

        gc.disable()
        times_5sub = []
        for _ in range(iterations):
            start = time.perf_counter()
            bus.publish("test.topic", data)
            times_5sub.append(time.perf_counter() - start)
        gc.enable()

        sub5_us = statistics.mean(times_5sub) * 1e6

        print(f"  0 subscribers: {empty_us:.3f}μs")
        print(f"  1 subscriber: {sub1_us:.3f}μs")
        print(f"  5 subscribers: {sub5_us:.3f}μs")

        self.results.append(BenchmarkResult(
            name="event_bus_0_subs",
            iterations=iterations,
            total_time_ms=sum(times_empty) * 1000,
            per_call_us=empty_us,
            min_us=min(times_empty) * 1e6,
            max_us=max(times_empty) * 1e6,
            stddev_us=statistics.stdev(times_empty) * 1e6,
        ))

        self.results.append(BenchmarkResult(
            name="event_bus_5_subs",
            iterations=iterations,
            total_time_ms=sum(times_5sub) * 1000,
            per_call_us=sub5_us,
            min_us=min(times_5sub) * 1e6,
            max_us=max(times_5sub) * 1e6,
            stddev_us=statistics.stdev(times_5sub) * 1e6,
        ))

    def bench_protocol_encode(self) -> None:
        """Measure protocol frame encoding overhead."""
        print("\n--- Protocol Framing ---")

        from mara_host.core.protocol import encode, MSG_CMD_JSON, MSG_CMD_BIN

        iterations = 10000
        json_payload = b'{"kind":"cmd","type":"CMD_SET_VEL","seq":123,"vx":0.5,"omega":0.1}'
        bin_payload = struct.pack("<Bff", 0x10, 0.5, 0.1)

        # JSON frame
        gc.disable()
        times_json = []
        for _ in range(iterations):
            start = time.perf_counter()
            frame = encode(MSG_CMD_JSON, json_payload)
            times_json.append(time.perf_counter() - start)
        gc.enable()

        json_frame_size = len(frame)
        json_us = statistics.mean(times_json) * 1e6

        # Binary frame
        gc.disable()
        times_bin = []
        for _ in range(iterations):
            start = time.perf_counter()
            frame = encode(MSG_CMD_BIN, bin_payload)
            times_bin.append(time.perf_counter() - start)
        gc.enable()

        bin_frame_size = len(frame)
        bin_us = statistics.mean(times_bin) * 1e6

        print(f"  JSON frame: {json_us:.3f}μs, {json_frame_size} bytes total")
        print(f"  Binary frame: {bin_us:.3f}μs, {bin_frame_size} bytes total")

        self.results.append(BenchmarkResult(
            name="protocol_encode_json",
            iterations=iterations,
            total_time_ms=sum(times_json) * 1000,
            per_call_us=json_us,
            extra={"frame_bytes": json_frame_size},
        ))

        self.results.append(BenchmarkResult(
            name="protocol_encode_binary",
            iterations=iterations,
            total_time_ms=sum(times_bin) * 1000,
            per_call_us=bin_us,
            extra={"frame_bytes": bin_frame_size},
        ))

    def bench_dict_operations(self) -> None:
        """Measure dict copy overhead (ReliableCommander issue)."""
        print("\n--- Dict Operations ---")

        iterations = 100000
        payload = {"vx": 0.5, "omega": 0.1}

        # Dict copy (current behavior)
        gc.disable()
        times_copy = []
        for _ in range(iterations):
            start = time.perf_counter()
            p = dict(payload)
            p["wantAck"] = False
            times_copy.append(time.perf_counter() - start)
        gc.enable()

        copy_us = statistics.mean(times_copy) * 1e6

        # In-place mutation (proposed)
        gc.disable()
        times_inplace = []
        for _ in range(iterations):
            start = time.perf_counter()
            payload["wantAck"] = False
            times_inplace.append(time.perf_counter() - start)
        gc.enable()

        inplace_us = statistics.mean(times_inplace) * 1e6

        print(f"  dict() copy + mutate: {copy_us:.3f}μs")
        print(f"  in-place mutate: {inplace_us:.3f}μs")
        print(f"  Savings: {copy_us - inplace_us:.3f}μs per call")

        self.results.append(BenchmarkResult(
            name="dict_copy",
            iterations=iterations,
            total_time_ms=sum(times_copy) * 1000,
            per_call_us=copy_us,
        ))

    async def bench_velocity_latency(self) -> None:
        """Measure end-to-end velocity command latency (requires hardware)."""
        print("\n--- Velocity Command Latency (Hardware) ---")

        from mara_host import Robot

        try:
            robot = Robot(port=self.port)
            await robot.connect()

            # Warm up
            for _ in range(50):
                await robot.motion.set_velocity(0.0, 0.0)

            # Benchmark
            iterations = 500
            gc.disable()
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                await robot.motion.set_velocity(0.1, 0.0)
                times.append(time.perf_counter() - start)
            gc.enable()

            await robot.disconnect()

            vel_us = statistics.mean(times) * 1e6
            print(f"  set_velocity latency: {vel_us:.2f}μs")
            print(f"  min/max: {min(times)*1e6:.2f}/{max(times)*1e6:.2f}μs")
            print(f"  Max sustainable rate: {1e6/vel_us:.0f} Hz")

            self.results.append(BenchmarkResult(
                name="velocity_e2e_latency",
                iterations=iterations,
                total_time_ms=sum(times) * 1000,
                per_call_us=vel_us,
                min_us=min(times) * 1e6,
                max_us=max(times) * 1e6,
                stddev_us=statistics.stdev(times) * 1e6,
            ))

        except Exception as e:
            print(f"  [ERROR] {e}")

    async def bench_transport_overhead(self) -> None:
        """Measure transport layer overhead (requires hardware)."""
        print("\n--- Transport Layer Overhead ---")

        from mara_host.transport.serial_transport import SerialTransport
        from mara_host.core.protocol import encode, MSG_CMD_BIN
        import struct

        try:
            transport = SerialTransport(port=self.port, baudrate=115200)
            await transport.open()

            # Small frame
            small_frame = encode(MSG_CMD_BIN, struct.pack("<Bff", 0x10, 0.5, 0.1))

            iterations = 500
            gc.disable()
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                await transport.send_bytes(small_frame)
                times.append(time.perf_counter() - start)
            gc.enable()

            await transport.close()

            send_us = statistics.mean(times) * 1e6
            print(f"  send_bytes latency: {send_us:.2f}μs")
            print(f"  (includes executor overhead)")

            self.results.append(BenchmarkResult(
                name="transport_send_bytes",
                iterations=iterations,
                total_time_ms=sum(times) * 1000,
                per_call_us=send_us,
                min_us=min(times) * 1e6,
                max_us=max(times) * 1e6,
                stddev_us=statistics.stdev(times) * 1e6,
            ))

        except Exception as e:
            print(f"  [ERROR] {e}")

    def print_summary(self) -> None:
        """Print summary of all benchmarks."""
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        for r in self.results:
            extra = ""
            if "bytes" in r.extra:
                extra = f" ({r.extra['bytes']} bytes)"
            elif "frame_bytes" in r.extra:
                extra = f" ({r.extra['frame_bytes']} bytes)"
            print(f"  {r.name}: {r.per_call_us:.2f}μs{extra}")

        # Save to file
        output_path = Path(__file__).parent / "efficiency_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([{
                "name": r.name,
                "per_call_us": r.per_call_us,
                "iterations": r.iterations,
                "extra": r.extra,
            } for r in self.results], f, indent=2)
        print(f"\nResults saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="MARA Host Efficiency Evaluator")
    parser.add_argument("--port", help="Serial port for hardware tests")
    args = parser.parse_args()

    evaluator = EfficiencyEvaluator(port=args.port)
    evaluator.run_all()


if __name__ == "__main__":
    main()
