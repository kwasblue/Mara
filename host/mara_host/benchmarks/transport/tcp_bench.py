# mara_host/benchmarks/transport/tcp_bench.py
"""
TCP transport benchmark - establishes baseline for WiFi/TCP communication.

Category: Integration
Measures: TCP transport send latency, throughput, and reliability.

Usage:
    python -m mara_host.benchmarks.transport.tcp_bench --host 192.168.4.1 --count 500
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


class TcpBenchmark:
    """TCP transport performance benchmark."""

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
            name="tcp_send_latency",
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
            name="tcp_rtt",
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

    async def measure_jitter(
        self,
        count: int = 100,
        timeout: float = 2.0,
    ) -> BenchmarkResult:
        """
        Measure RTT jitter (variance in latency).

        Returns:
            BenchmarkResult with jitter statistics
        """
        loop = asyncio.get_running_loop()
        times_ms: List[float] = []

        for _ in range(count):
            self._pong_received = loop.create_future()
            self._t_sent = time.perf_counter()
            await self._client.send_ping()

            try:
                t_recv = await asyncio.wait_for(self._pong_received, timeout)
                rtt_ms = (t_recv - self._t_sent) * 1000.0
                times_ms.append(rtt_ms)
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(0.05)

        return make_result(
            name="tcp_jitter",
            times_ms=times_ms,
            metadata={"measurement": "jitter"},
        )


async def run_benchmark(
    host: str,
    port: int = 3333,
    count: int = 500,
    timeout: float = 2.0,
    save_report: bool = True,
) -> dict[str, BenchmarkResult]:
    """
    Run TCP transport benchmark.

    Args:
        host: TCP host address
        port: TCP port
        count: Number of messages per test
        timeout: Timeout per message
        save_report: Whether to save JSON report
    """
    from mara_host.transport.tcp_transport import AsyncTcpTransport

    print_header("TCP Transport Benchmark")
    print(f"  Host: {host}:{port}")
    print(f"  Iterations: {count}")

    bus = EventBus()
    transport = AsyncTcpTransport(host=host, port=port)
    client = MaraClient(transport=transport, bus=bus)

    results = {}

    try:
        await client.start()
        # Give TCP connection time to stabilize
        await asyncio.sleep(0.5)
        print("\n  Client connected")

        benchmark = TcpBenchmark(client, bus)

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

        # Test 3: Jitter
        print_section("Jitter Analysis")
        jitter_result = await benchmark.measure_jitter(count=100, timeout=timeout)
        print(f"  Jitter (stddev): {jitter_result.jitter_ms:.2f}ms")
        print(f"  Min RTT: {jitter_result.min_ms:.2f}ms")
        print(f"  Max RTT: {jitter_result.max_ms:.2f}ms")
        results["jitter"] = jitter_result

        # Test 4: Throughput
        print_section("Throughput (5 second burst)")
        throughput, throughput_errors = await benchmark.measure_throughput(duration_s=5.0)
        print(f"  Throughput: {throughput:.1f} msgs/sec")
        print(f"  Errors: {throughput_errors}")

        # Save report
        if save_report:
            env = BenchmarkEnvironment.capture(
                transport="tcp",
                port_or_host=f"{host}:{port}",
                baud_rate=None,
                protocol="json",
            )

            rtt_result.metadata["send_latency_ms"] = send_result.mean_ms
            rtt_result.metadata["throughput_hz"] = throughput
            rtt_result.metadata["jitter_ms"] = jitter_result.jitter_ms
            rtt_result.throughput_hz = throughput

            report = BenchmarkReport(
                benchmark="tcp_transport",
                environment=env,
                results=rtt_result,
            )
            filepath = report.save()
            print(f"\n  Report saved: {filepath}")

        return results

    finally:
        await client.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="TCP Transport Benchmark")
    parser.add_argument("--host", "-H", required=True, help="TCP host address")
    parser.add_argument("--port", "-P", type=int, default=3333, help="TCP port")
    parser.add_argument("--count", "-n", type=int, default=500, help="Message count")
    parser.add_argument("--timeout", "-t", type=float, default=2.0, help="Timeout per message")
    parser.add_argument("--no-save", action="store_true", help="Don't save report")

    args = parser.parse_args()

    asyncio.run(
        run_benchmark(
            host=args.host,
            port=args.port,
            count=args.count,
            timeout=args.timeout,
            save_report=not args.no_save,
        )
    )


if __name__ == "__main__":
    main()
