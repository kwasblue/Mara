# mara_host/benchmarks/commands/ping_rtt.py
"""
Ping RTT benchmark - measures basic round-trip latency through the full stack.

Category: Integration
Measures: Basic round-trip latency including transport, protocol, and MCU processing.

Usage:
    python -m mara_host.benchmarks.commands.ping_rtt --port /dev/tty.usbserial --count 500
    python -m mara_host.benchmarks.commands.ping_rtt --tcp 192.168.4.1:3333 --count 100
"""

from __future__ import annotations

import argparse
import asyncio
import time
from typing import Optional

from mara_host.core.event_bus import EventBus
from mara_host.logger import get_logger

logger = get_logger("benchmarks.ping_rtt")
from mara_host.command.client import MaraClient
from mara_host.benchmarks.core import (
    BenchmarkEnvironment,
    BenchmarkReport,
    BenchmarkResult,
    make_result,
    print_header,
    print_result,
)


class PingBenchmark:
    """Measures ping/pong round-trip latency."""

    def __init__(self, client: MaraClient, bus: EventBus) -> None:
        self._client = client
        self._bus = bus
        self._pending: Optional[asyncio.Future[float]] = None
        self._t_sent: float = 0.0

        # Subscribe to pong responses
        bus.subscribe("pong", self._on_pong)

    def _on_pong(self, msg: dict) -> None:
        """Handle pong response."""
        if self._pending is None or self._pending.done():
            return

        t_arrive = time.perf_counter()
        self._pending.set_result(t_arrive)

    async def measure_once(self, timeout: float = 2.0) -> tuple[Optional[float], bool]:
        """
        Send one ping and measure round-trip.

        Returns:
            (rtt_ms, success) tuple
        """
        loop = asyncio.get_running_loop()
        self._pending = loop.create_future()

        self._t_sent = time.perf_counter()
        await self._client.send_ping()

        try:
            t_arrive = await asyncio.wait_for(self._pending, timeout)
            rtt_ms = (t_arrive - self._t_sent) * 1000.0
            return rtt_ms, True
        except asyncio.TimeoutError:
            return None, False
        finally:
            self._pending = None

    async def run(
        self,
        count: int = 500,
        timeout: float = 2.0,
        delay: float = 0.05,
        warmup: int = 10,
    ) -> BenchmarkResult:
        """
        Run ping benchmark.

        Args:
            count: Number of pings to send
            timeout: Timeout per ping in seconds
            delay: Delay between pings in seconds
            warmup: Number of warmup pings (not counted)

        Returns:
            BenchmarkResult with timing statistics
        """
        # Warmup
        for _ in range(warmup):
            await self.measure_once(timeout)
            await asyncio.sleep(delay)

        times_ms: list[float] = []
        timeouts = 0

        for i in range(count):
            rtt_ms, ok = await self.measure_once(timeout)
            if ok and rtt_ms is not None:
                times_ms.append(rtt_ms)
            else:
                timeouts += 1

            if delay > 0:
                await asyncio.sleep(delay)

            # Progress indicator every 100 pings
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{count}")

        return make_result(
            name="ping_rtt",
            times_ms=times_ms,
            error_count=timeouts,
            throughput_hz=len(times_ms) / sum(times_ms) * 1000 if times_ms else None,
            metadata={"timeout_count": timeouts, "warmup": warmup},
        )


async def run_benchmark(
    port: Optional[str] = None,
    tcp_host: Optional[str] = None,
    tcp_port: int = 3333,
    count: int = 500,
    timeout: float = 2.0,
    delay: float = 0.05,
    warmup: int = 10,
    save_report: bool = True,
) -> BenchmarkResult:
    """
    Run ping RTT benchmark.

    Args:
        port: Serial port (e.g., /dev/tty.usbserial)
        tcp_host: TCP host (e.g., 192.168.4.1)
        tcp_port: TCP port (default 3333)
        count: Number of pings
        timeout: Timeout per ping
        delay: Delay between pings
        warmup: Warmup iterations
        save_report: Whether to save JSON report

    Returns:
        BenchmarkResult
    """
    bus = EventBus()

    # Create appropriate transport
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

    client = MaraClient(transport=transport, bus=bus)

    print_header("Ping RTT Benchmark")
    print(f"  Transport: {transport_type}")
    print(f"  Target: {port_or_host}")
    print(f"  Iterations: {count}")
    print(f"  Warmup: {warmup}")

    try:
        try:
            await asyncio.wait_for(client.start(), timeout=10.0)
        except asyncio.TimeoutError:
            print("\n  ERROR: Connection timed out after 10s")
            raise RuntimeError("Connection timeout")
        print("\n  Client connected, measuring RTT...")

        benchmark = PingBenchmark(client, bus)
        result = await benchmark.run(
            count=count,
            timeout=timeout,
            delay=delay,
            warmup=warmup,
        )

        print()
        print_result(result)

        if save_report:
            env = BenchmarkEnvironment.capture(
                transport=transport_type,
                port_or_host=port_or_host,
                baud_rate=baud_rate,
                protocol="binary",
            )
            report = BenchmarkReport(
                benchmark="ping_rtt",
                environment=env,
                results=result,
            )
            filepath = report.save()
            print(f"\n  Report saved: {filepath}")

        return result

    finally:
        await client.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ping RTT Benchmark")
    parser.add_argument("--port", "-p", help="Serial port (e.g., /dev/tty.usbserial)")
    parser.add_argument("--tcp", help="TCP host:port (e.g., 192.168.4.1:3333)")
    parser.add_argument("--count", "-n", type=int, default=500, help="Number of pings")
    parser.add_argument("--timeout", "-t", type=float, default=2.0, help="Timeout per ping (seconds)")
    parser.add_argument("--delay", "-d", type=float, default=0.05, help="Delay between pings (seconds)")
    parser.add_argument("--warmup", "-w", type=int, default=10, help="Warmup iterations")
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
            count=args.count,
            timeout=args.timeout,
            delay=args.delay,
            warmup=args.warmup,
            save_report=not args.no_save,
        )
    )


if __name__ == "__main__":
    main()
