# mara_host/benchmarks/streaming/sustained_stream.py
"""
Sustained stream benchmark - measures performance under continuous command load.

Category: Integration
Measures: Stream rate sustainability, latency degradation, and reliability.

Usage:
    python -m mara_host.benchmarks.streaming.sustained_stream \
        --port /dev/tty.usbserial --rate 50 --duration 30
"""

from __future__ import annotations

import argparse
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mara_host.core.event_bus import EventBus
from mara_host.logger import get_logger

logger = get_logger("benchmarks.streaming")
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


@dataclass
class StreamStats:
    """Statistics from a streaming benchmark run."""

    requested_rate_hz: float
    achieved_rate_hz: float
    duration_s: float
    total_sent: int
    total_dropped: int
    total_skipped: int
    ttl_expired: int
    errors: int

    # Latency tracking
    latency_samples: List[float] = field(default_factory=list)
    queue_depth_samples: List[int] = field(default_factory=list)

    @property
    def rate_achievement_pct(self) -> float:
        """Percentage of requested rate achieved."""
        return (self.achieved_rate_hz / self.requested_rate_hz * 100) if self.requested_rate_hz > 0 else 0

    @property
    def drop_rate_pct(self) -> float:
        """Percentage of commands dropped."""
        total = self.total_sent + self.total_dropped
        return (self.total_dropped / total * 100) if total > 0 else 0


class StreamingBenchmark:
    """Benchmarks sustained command streaming."""

    def __init__(self, client: MaraClient, bus: EventBus) -> None:
        self._client = client
        self._bus = bus

    async def run_fire_and_forget_stream(
        self,
        rate_hz: float,
        duration_s: float,
        cmd_type: str = "CMD_HEARTBEAT",
        payload: Optional[Dict[str, Any]] = None,
    ) -> StreamStats:
        """
        Stream commands at a fixed rate using fire-and-forget.

        Args:
            rate_hz: Target command rate
            duration_s: Test duration
            cmd_type: Command type to stream
            payload: Command payload

        Returns:
            StreamStats with results
        """
        if payload is None:
            payload = {}

        period = 1.0 / rate_hz
        start_time = time.perf_counter()
        end_time = start_time + duration_s
        next_send = start_time

        total_sent = 0
        errors = 0
        latencies: List[float] = []

        print(f"    Streaming {cmd_type} at {rate_hz} Hz for {duration_s}s...")

        # Safety limit: max iterations to prevent infinite loops
        max_iterations = int(rate_hz * duration_s * 2) + 1000
        iteration = 0

        while time.perf_counter() < end_time and iteration < max_iterations:
            iteration += 1
            now = time.perf_counter()

            if now >= next_send:
                send_start = time.perf_counter_ns()
                try:
                    # Timeout on individual send to prevent hanging
                    await asyncio.wait_for(
                        self._client.send_json_cmd(cmd_type, payload),
                        timeout=1.0,
                    )
                    total_sent += 1
                    latencies.append((time.perf_counter_ns() - send_start) / 1_000_000.0)
                except asyncio.TimeoutError:
                    errors += 1
                    logger.warning("Send timed out after 1s")
                except Exception as e:
                    errors += 1
                    logger.debug(f"Send error: {e}")

                next_send += period

                # If we've fallen behind, reset to now
                if next_send < now:
                    next_send = now + period

            # Brief yield to event loop
            sleep_time = max(0.0001, min(next_send - time.perf_counter(), 0.1))
            await asyncio.sleep(sleep_time)

        actual_duration = time.perf_counter() - start_time
        achieved_rate = total_sent / actual_duration if actual_duration > 0 else 0

        return StreamStats(
            requested_rate_hz=rate_hz,
            achieved_rate_hz=achieved_rate,
            duration_s=actual_duration,
            total_sent=total_sent,
            total_dropped=0,
            total_skipped=0,
            ttl_expired=0,
            errors=errors,
            latency_samples=latencies,
        )

    async def run_reliable_stream(
        self,
        rate_hz: float,
        duration_s: float,
        cmd_type: str = "CMD_HEARTBEAT",
        payload: Optional[Dict[str, Any]] = None,
        timeout_s: float = 0.5,
    ) -> StreamStats:
        """
        Stream commands at a fixed rate with ACK verification.

        This mode is slower but verifies command delivery.

        Args:
            rate_hz: Target command rate
            duration_s: Test duration
            cmd_type: Command type to stream
            payload: Command payload
            timeout_s: ACK timeout

        Returns:
            StreamStats with results
        """
        if payload is None:
            payload = {}

        period = 1.0 / rate_hz
        start_time = time.perf_counter()
        end_time = start_time + duration_s
        next_send = start_time

        total_sent = 0
        dropped = 0
        errors = 0
        latencies: List[float] = []
        queue_depths: List[int] = []

        print(f"    Streaming {cmd_type} at {rate_hz} Hz (reliable) for {duration_s}s...")

        # Safety limit: max iterations to prevent infinite loops
        max_iterations = int(rate_hz * duration_s * 2) + 1000
        iteration = 0
        skipped_total = 0

        while time.perf_counter() < end_time and iteration < max_iterations:
            iteration += 1
            now = time.perf_counter()

            if now >= next_send:
                send_start = time.perf_counter_ns()

                # Track queue depth if available
                if hasattr(self._client, "commander"):
                    depth = self._client.commander.pending_count()
                    queue_depths.append(depth)

                try:
                    # Use the provided timeout, but cap it to prevent very long hangs
                    effective_timeout = min(timeout_s, 5.0)
                    ok, _ = await asyncio.wait_for(
                        self._client.send_reliable(
                            cmd_type,
                            payload,
                            wait_for_ack=True,
                            timeout_s=effective_timeout,
                        ),
                        timeout=effective_timeout + 1.0,
                    )
                    if ok:
                        total_sent += 1
                        latencies.append((time.perf_counter_ns() - send_start) / 1_000_000.0)
                    else:
                        dropped += 1
                except asyncio.TimeoutError:
                    errors += 1
                    logger.warning("Reliable send timed out")
                except Exception as e:
                    errors += 1
                    logger.debug(f"Reliable send error: {e}")

                next_send += period

                # If we've fallen behind, skip to current time
                if next_send < now:
                    skipped_count = int((now - next_send) / period)
                    skipped_total += skipped_count
                    next_send = now + period

            # Shorter sleep for tighter timing, capped to prevent long sleeps
            sleep_time = max(0.001, min(next_send - time.perf_counter(), 0.1))
            await asyncio.sleep(sleep_time)

        actual_duration = time.perf_counter() - start_time
        achieved_rate = total_sent / actual_duration if actual_duration > 0 else 0

        return StreamStats(
            requested_rate_hz=rate_hz,
            achieved_rate_hz=achieved_rate,
            duration_s=actual_duration,
            total_sent=total_sent,
            total_dropped=dropped,
            total_skipped=skipped_total,
            ttl_expired=0,
            errors=errors,
            latency_samples=latencies,
            queue_depth_samples=queue_depths,
        )

    async def find_max_sustainable_rate(
        self,
        start_rate: float = 10.0,
        max_rate: float = 200.0,
        step: float = 10.0,
        test_duration: float = 3.0,
        threshold_pct: float = 95.0,
    ) -> float:
        """
        Find maximum sustainable command rate.

        Increases rate until achievement drops below threshold.

        Args:
            start_rate: Starting rate to test
            max_rate: Maximum rate to test
            step: Rate increment per test
            test_duration: Duration per test
            threshold_pct: Minimum achievement percentage

        Returns:
            Maximum sustainable rate in Hz
        """
        print(f"    Finding max sustainable rate (threshold={threshold_pct}%)...")

        current_rate = start_rate
        best_rate = start_rate

        while current_rate <= max_rate:
            stats = await self.run_fire_and_forget_stream(
                rate_hz=current_rate,
                duration_s=test_duration,
            )

            achievement = stats.rate_achievement_pct
            print(f"      {current_rate:.0f} Hz: achieved {stats.achieved_rate_hz:.1f} Hz ({achievement:.1f}%)")

            if achievement >= threshold_pct:
                best_rate = current_rate
                current_rate += step
            else:
                break

            # Brief pause between tests
            await asyncio.sleep(0.5)

        return best_rate


async def run_benchmark(
    port: Optional[str] = None,
    tcp_host: Optional[str] = None,
    tcp_port: int = 3333,
    rate: float = 50.0,
    duration: float = 30.0,
    reliable: bool = False,
    find_max: bool = False,
    save_report: bool = True,
) -> StreamStats:
    """
    Run sustained streaming benchmark.

    Args:
        port: Serial port
        tcp_host: TCP host
        tcp_port: TCP port
        rate: Target command rate
        duration: Test duration
        reliable: Use ACK-verified sending
        find_max: Find maximum sustainable rate
        save_report: Whether to save JSON report
    """
    bus = EventBus()

    # Create transport
    if port:
        from mara_host.transport.serial_transport import SerialTransport

        transport = SerialTransport(port=port, baudrate=115200)
        transport_type = "serial"
        port_or_host = port
        baud_rate = 115200
    elif tcp_host:
        from mara_host.transport.tcp_transport import AsyncTcpTransport

        transport = AsyncTcpTransport(host=tcp_host, port=tcp_port)
        transport_type = "tcp"
        port_or_host = f"{tcp_host}:{tcp_port}"
        baud_rate = None
    else:
        raise ValueError("Must specify either --port or --tcp")

    print_header("Sustained Stream Benchmark")
    print(f"  Transport: {transport_type}")
    print(f"  Target: {port_or_host}")
    print(f"  Mode: {'reliable (ACK)' if reliable else 'fire-and-forget'}")

    client = MaraClient(transport=transport, bus=bus)

    try:
        # Timeout on connection to prevent indefinite hang
        try:
            await asyncio.wait_for(client.start(), timeout=10.0)
        except asyncio.TimeoutError:
            print("\n  ERROR: Connection timed out after 10s")
            raise RuntimeError("Connection timeout")

        if tcp_host:
            await asyncio.sleep(0.5)  # TCP stabilization
        print("\n  Client connected")

        benchmark = StreamingBenchmark(client, bus)

        # Find max rate if requested
        if find_max:
            print_section("Maximum Rate Discovery")
            max_rate = await benchmark.find_max_sustainable_rate()
            print(f"\n    Maximum sustainable rate: {max_rate:.0f} Hz")
            rate = max_rate  # Use discovered rate for main test

        # Main benchmark
        print_section(f"Sustained Stream Test ({rate} Hz, {duration}s)")

        if reliable:
            stats = await benchmark.run_reliable_stream(
                rate_hz=rate,
                duration_s=duration,
            )
        else:
            stats = await benchmark.run_fire_and_forget_stream(
                rate_hz=rate,
                duration_s=duration,
            )

        # Print results
        print()
        print(f"  Requested rate: {stats.requested_rate_hz:.1f} Hz")
        print(f"  Achieved rate:  {stats.achieved_rate_hz:.1f} Hz ({stats.rate_achievement_pct:.1f}%)")
        print(f"  Total sent:     {stats.total_sent}")
        print(f"  Dropped:        {stats.total_dropped}")
        print(f"  Errors:         {stats.errors}")

        if stats.latency_samples:
            import statistics

            sorted_lat = sorted(stats.latency_samples)
            print_section("Send Latency Under Load")
            print(f"  Mean:   {statistics.mean(sorted_lat):.2f}ms")
            print(f"  P50:    {sorted_lat[len(sorted_lat) // 2]:.2f}ms")
            print(f"  P95:    {sorted_lat[int(len(sorted_lat) * 0.95)]:.2f}ms")
            print(f"  P99:    {sorted_lat[int(len(sorted_lat) * 0.99)]:.2f}ms")
            print(f"  Max:    {max(sorted_lat):.2f}ms")

        if stats.queue_depth_samples:
            import statistics

            print_section("Queue Depth")
            print(f"  Mean:   {statistics.mean(stats.queue_depth_samples):.1f}")
            print(f"  Max:    {max(stats.queue_depth_samples)}")

        # Save report
        if save_report:
            env = BenchmarkEnvironment.capture(
                transport=transport_type,
                port_or_host=port_or_host,
                baud_rate=baud_rate,
                protocol="json",
            )

            result = make_result(
                name="sustained_stream",
                times_ms=stats.latency_samples if stats.latency_samples else [0],
                error_count=stats.errors + stats.total_dropped,
                throughput_hz=stats.achieved_rate_hz,
                metadata={
                    "requested_rate_hz": stats.requested_rate_hz,
                    "achieved_rate_hz": stats.achieved_rate_hz,
                    "rate_achievement_pct": stats.rate_achievement_pct,
                    "total_sent": stats.total_sent,
                    "total_dropped": stats.total_dropped,
                    "duration_s": stats.duration_s,
                    "mode": "reliable" if reliable else "fire_and_forget",
                },
            )

            report = BenchmarkReport(
                benchmark="sustained_stream",
                environment=env,
                results=result,
            )
            filepath = report.save()
            print(f"\n  Report saved: {filepath}")

        return stats

    finally:
        await client.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sustained Stream Benchmark")
    parser.add_argument("--port", "-p", help="Serial port")
    parser.add_argument("--tcp", help="TCP host:port")
    parser.add_argument("--rate", "-r", type=float, default=50.0, help="Target rate (Hz)")
    parser.add_argument("--duration", "-d", type=float, default=30.0, help="Test duration (seconds)")
    parser.add_argument("--reliable", action="store_true", help="Use ACK-verified sending")
    parser.add_argument("--find-max", action="store_true", help="Find maximum sustainable rate")
    parser.add_argument("--no-save", action="store_true", help="Don't save report")

    args = parser.parse_args()

    tcp_host = None
    tcp_port = 3333
    if args.tcp:
        if ":" in args.tcp:
            tcp_host, tcp_port_str = args.tcp.rsplit(":", 1)
            try:
                tcp_port = int(tcp_port_str)
            except ValueError:
                parser.error(f"Invalid TCP port: {tcp_port_str}")
        else:
            tcp_host = args.tcp

    if not args.port and not tcp_host:
        parser.error("Must specify either --port or --tcp")

    asyncio.run(
        run_benchmark(
            port=args.port,
            tcp_host=tcp_host,
            tcp_port=tcp_port,
            rate=args.rate,
            duration=args.duration,
            reliable=args.reliable,
            find_max=args.find_max,
            save_report=not args.no_save,
        )
    )


if __name__ == "__main__":
    main()
