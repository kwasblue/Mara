# mara_host/benchmarks/transport/serial_bench.py
"""
Serial transport benchmark - establishes baseline for serial communication.

Category: Integration
Measures: Serial transport send latency, throughput, and reliability.

Usage:
    python -m mara_host.benchmarks.transport.serial_bench --port /dev/tty.usbserial --count 500
"""

from __future__ import annotations

import argparse
import asyncio
import time
from typing import List, Optional

from mara_host.core.event_bus import EventBus
from mara_host.command.client import MaraClient
from mara_host.benchmarks.core import (
    BenchmarkEnvironment,
    BenchmarkReport,
    BenchmarkResult,
    make_result,
    print_header,
    print_result,
    print_section,
)


class SerialBenchmark:
    """Serial transport performance benchmark."""

    def __init__(self, client: MaraClient, bus: EventBus) -> None:
        self._client = client
        self._bus = bus
        self._pong_received: Optional[asyncio.Future[float]] = None
        self._t_sent: float = 0.0

        bus.subscribe("pong", self._on_pong)

    def _on_pong(self, msg: dict) -> None:
        if self._pong_received and not self._pong_received.done():
            self._pong_received.set_result(time.perf_counter())

    async def measure_send_latency(
        self,
        count: int = 100,
        warmup: int = 10,
    ) -> tuple[BenchmarkResult, int]:
        """
        Measure one-way send latency (fire-and-forget).

        Returns:
            (BenchmarkResult, errors)
        """
        # Warmup
        for _ in range(warmup):
            await self._client.send_json_cmd("CMD_HEARTBEAT", {})
            await asyncio.sleep(0.01)

        times_ms: List[float] = []
        errors = 0

        for _ in range(count):
            try:
                start = time.perf_counter_ns()
                await self._client.send_json_cmd("CMD_HEARTBEAT", {})
                elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
                times_ms.append(elapsed_ms)
            except Exception:
                errors += 1
            await asyncio.sleep(0.01)

        result = make_result(
            name="serial_send_latency",
            times_ms=times_ms,
            error_count=errors,
        )
        return result, errors

    async def measure_rtt(
        self,
        count: int = 100,
        timeout: float = 2.0,
        warmup: int = 10,
    ) -> tuple[BenchmarkResult, int]:
        """
        Measure round-trip time using ping/pong.

        Returns:
            (BenchmarkResult, timeouts)
        """
        loop = asyncio.get_running_loop()

        # Warmup
        for _ in range(warmup):
            self._pong_received = loop.create_future()
            await self._client.send_ping()
            try:
                await asyncio.wait_for(self._pong_received, timeout)
            except asyncio.TimeoutError:
                pass
            await asyncio.sleep(0.05)

        times_ms: List[float] = []
        timeouts = 0

        for _ in range(count):
            self._pong_received = loop.create_future()
            self._t_sent = time.perf_counter()
            await self._client.send_ping()

            try:
                t_recv = await asyncio.wait_for(self._pong_received, timeout)
                rtt_ms = (t_recv - self._t_sent) * 1000.0
                times_ms.append(rtt_ms)
            except asyncio.TimeoutError:
                timeouts += 1

            await asyncio.sleep(0.02)

        result = make_result(
            name="serial_rtt",
            times_ms=times_ms,
            error_count=timeouts,
            throughput_hz=len(times_ms) / sum(times_ms) * 1000 if times_ms else None,
        )
        return result, timeouts

    async def measure_throughput(
        self,
        duration_s: float = 5.0,
    ) -> tuple[float, int]:
        """
        Measure maximum message throughput.

        Returns:
            (msgs_per_sec, errors)
        """
        start = time.perf_counter()
        count = 0
        errors = 0

        while (time.perf_counter() - start) < duration_s:
            try:
                await self._client.send_json_cmd("CMD_HEARTBEAT", {})
                count += 1
            except Exception:
                errors += 1
            # Minimal delay to prevent flooding
            await asyncio.sleep(0.001)

        elapsed = time.perf_counter() - start
        throughput = count / elapsed if elapsed > 0 else 0

        return throughput, errors


async def run_benchmark(
    port: str,
    baudrate: int = 115200,
    count: int = 500,
    timeout: float = 2.0,
    save_report: bool = True,
) -> dict[str, BenchmarkResult]:
    """
    Run serial transport benchmark.

    Args:
        port: Serial port path
        baudrate: Baud rate
        count: Number of messages per test
        timeout: Timeout per message
        save_report: Whether to save JSON report
    """
    from mara_host.transport.serial_transport import SerialTransport

    print_header("Serial Transport Benchmark")
    print(f"  Port: {port}")
    print(f"  Baud rate: {baudrate}")
    print(f"  Iterations: {count}")

    bus = EventBus()
    transport = SerialTransport(port=port, baudrate=baudrate)
    client = MaraClient(transport=transport, bus=bus)

    results = {}

    try:
        await client.start()
        print("\n  Client connected")

        benchmark = SerialBenchmark(client, bus)

        # Test 1: Send latency
        print_section("Send Latency (fire-and-forget)")
        send_result, send_errors = await benchmark.measure_send_latency(count=count // 2)
        print_result(send_result)
        results["send_latency"] = send_result

        # Test 2: Round-trip time
        print_section("Round-Trip Time (ping/pong)")
        rtt_result, rtt_timeouts = await benchmark.measure_rtt(count=count, timeout=timeout)
        print_result(rtt_result)
        results["rtt"] = rtt_result

        # Test 3: Throughput
        print_section("Throughput (5 second burst)")
        throughput, throughput_errors = await benchmark.measure_throughput(duration_s=5.0)
        print(f"  Throughput: {throughput:.1f} msgs/sec")
        print(f"  Errors: {throughput_errors}")

        # Save report
        if save_report:
            env = BenchmarkEnvironment.capture(
                transport="serial",
                port_or_host=port,
                baud_rate=baudrate,
                protocol="json",
            )

            # Use RTT as the main result
            rtt_result.metadata["send_latency_ms"] = send_result.mean_ms
            rtt_result.metadata["throughput_hz"] = throughput
            rtt_result.throughput_hz = throughput

            report = BenchmarkReport(
                benchmark="serial_transport",
                environment=env,
                results=rtt_result,
            )
            filepath = report.save()
            print(f"\n  Report saved: {filepath}")

        return results

    finally:
        await client.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serial Transport Benchmark")
    parser.add_argument("--port", "-p", required=True, help="Serial port")
    parser.add_argument("--baudrate", "-b", type=int, default=115200, help="Baud rate")
    parser.add_argument("--count", "-n", type=int, default=500, help="Message count")
    parser.add_argument("--timeout", "-t", type=float, default=2.0, help="Timeout per message")
    parser.add_argument("--no-save", action="store_true", help="Don't save report")

    args = parser.parse_args()

    asyncio.run(
        run_benchmark(
            port=args.port,
            baudrate=args.baudrate,
            count=args.count,
            timeout=args.timeout,
            save_report=not args.no_save,
        )
    )


if __name__ == "__main__":
    main()
