# mara_host/benchmarks/transport/compare.py
"""
Transport comparison benchmark - apples-to-apples comparison of different transports.

Category: Integration
Measures: Same commands over different transports for direct comparison.

Usage:
    python -m mara_host.benchmarks.transport.compare \
        --serial /dev/tty.usbserial \
        --tcp 192.168.4.1:3333
"""

from __future__ import annotations

import argparse
import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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


@dataclass
class TransportMetrics:
    """Metrics for a single transport."""

    name: str
    send_latency_ms: float
    rtt_ms: float
    rtt_p95_ms: float
    rtt_p99_ms: float
    jitter_ms: float
    throughput_hz: float
    error_rate: float


async def benchmark_transport(
    client: MaraClient,
    bus: EventBus,
    transport_name: str,
    count: int = 200,
    timeout: float = 2.0,
) -> TransportMetrics:
    """
    Run standard benchmark suite on a transport.

    Returns:
        TransportMetrics with all measurements
    """
    pong_received: Optional[asyncio.Future[float]] = None
    t_sent: float = 0.0

    def on_pong(msg: dict) -> None:
        nonlocal pong_received
        if pong_received and not pong_received.done():
            pong_received.set_result(time.perf_counter())

    bus.subscribe("pong", on_pong)
    loop = asyncio.get_running_loop()

    # Warmup
    print(f"    Warming up {transport_name}...")
    for _ in range(20):
        pong_received = loop.create_future()
        await client.send_ping()
        try:
            await asyncio.wait_for(pong_received, timeout)
        except asyncio.TimeoutError:
            pass
        await asyncio.sleep(0.02)

    # 1. Send latency (fire-and-forget)
    send_times: List[float] = []
    for _ in range(count // 2):
        start = time.perf_counter_ns()
        await client.send_json_cmd("CMD_HEARTBEAT", {})
        send_times.append((time.perf_counter_ns() - start) / 1_000_000.0)
        await asyncio.sleep(0.01)

    # 2. RTT measurement
    rtt_times: List[float] = []
    timeouts = 0
    for _ in range(count):
        pong_received = loop.create_future()
        t_sent = time.perf_counter()
        await client.send_ping()

        try:
            t_recv = await asyncio.wait_for(pong_received, timeout)
            rtt_times.append((t_recv - t_sent) * 1000.0)
        except asyncio.TimeoutError:
            timeouts += 1

        await asyncio.sleep(0.02)

    # 3. Throughput test
    start = time.perf_counter()
    msg_count = 0
    throughput_errors = 0
    test_duration = 3.0

    while (time.perf_counter() - start) < test_duration:
        try:
            await client.send_json_cmd("CMD_HEARTBEAT", {})
            msg_count += 1
        except Exception:
            throughput_errors += 1
        await asyncio.sleep(0.001)

    elapsed = time.perf_counter() - start
    throughput = msg_count / elapsed if elapsed > 0 else 0

    # Calculate statistics
    import statistics

    sorted_rtt = sorted(rtt_times) if rtt_times else [0]

    def percentile(data: List[float], p: float) -> float:
        if not data:
            return 0.0
        k = (len(data) - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, len(data) - 1)
        return data[f] + (k - f) * (data[c] - data[f])

    return TransportMetrics(
        name=transport_name,
        send_latency_ms=statistics.mean(send_times) if send_times else 0,
        rtt_ms=statistics.mean(rtt_times) if rtt_times else 0,
        rtt_p95_ms=percentile(sorted_rtt, 95),
        rtt_p99_ms=percentile(sorted_rtt, 99),
        jitter_ms=statistics.stdev(rtt_times) if len(rtt_times) > 1 else 0,
        throughput_hz=throughput,
        error_rate=(timeouts + throughput_errors) / (count + msg_count) if (count + msg_count) > 0 else 0,
    )


async def run_comparison(
    serial_port: Optional[str] = None,
    serial_baudrate: int = 115200,
    tcp_host: Optional[str] = None,
    tcp_port: int = 3333,
    count: int = 200,
    timeout: float = 2.0,
    save_report: bool = True,
) -> Dict[str, TransportMetrics]:
    """
    Run comparison benchmark across available transports.

    Args:
        serial_port: Serial port path (optional)
        serial_baudrate: Baud rate for serial
        tcp_host: TCP host address (optional)
        tcp_port: TCP port
        count: Number of iterations per test
        timeout: Timeout per message
        save_report: Whether to save JSON report
    """
    print_header("Transport Comparison Benchmark")
    print(f"  Iterations per transport: {count}")

    results: Dict[str, TransportMetrics] = {}

    # Serial transport
    if serial_port:
        print_section(f"Serial ({serial_port})")
        from mara_host.transport.serial_transport import SerialTransport

        bus = EventBus()
        transport = SerialTransport(port=serial_port, baudrate=serial_baudrate)
        client = MaraClient(transport=transport, bus=bus)

        try:
            await client.start()
            metrics = await benchmark_transport(client, bus, "serial", count, timeout)
            results["serial"] = metrics

            print(f"    Send latency: {metrics.send_latency_ms:.2f}ms")
            print(f"    RTT: {metrics.rtt_ms:.2f}ms (p95={metrics.rtt_p95_ms:.2f}, p99={metrics.rtt_p99_ms:.2f})")
            print(f"    Jitter: {metrics.jitter_ms:.2f}ms")
            print(f"    Throughput: {metrics.throughput_hz:.1f} msgs/sec")
            print(f"    Error rate: {metrics.error_rate * 100:.2f}%")
        finally:
            await client.stop()

    # TCP transport
    if tcp_host:
        print_section(f"TCP ({tcp_host}:{tcp_port})")
        from mara_host.transport.tcp_transport import AsyncTcpTransport

        bus = EventBus()
        transport = AsyncTcpTransport(host=tcp_host, port=tcp_port)
        client = MaraClient(transport=transport, bus=bus)

        try:
            await client.start()
            await asyncio.sleep(0.5)  # Let TCP stabilize
            metrics = await benchmark_transport(client, bus, "tcp", count, timeout)
            results["tcp"] = metrics

            print(f"    Send latency: {metrics.send_latency_ms:.2f}ms")
            print(f"    RTT: {metrics.rtt_ms:.2f}ms (p95={metrics.rtt_p95_ms:.2f}, p99={metrics.rtt_p99_ms:.2f})")
            print(f"    Jitter: {metrics.jitter_ms:.2f}ms")
            print(f"    Throughput: {metrics.throughput_hz:.1f} msgs/sec")
            print(f"    Error rate: {metrics.error_rate * 100:.2f}%")
        finally:
            await client.stop()

    # Comparison summary
    if len(results) > 1:
        print_section("Comparison Summary")

        # Header
        print(f"  {'Metric':<20} ", end="")
        for name in results:
            print(f"{name:>12} ", end="")
        print()
        print("  " + "-" * (20 + 13 * len(results)))

        # Rows
        metrics_to_compare = [
            ("Send Latency (ms)", "send_latency_ms"),
            ("RTT (ms)", "rtt_ms"),
            ("RTT p95 (ms)", "rtt_p95_ms"),
            ("RTT p99 (ms)", "rtt_p99_ms"),
            ("Jitter (ms)", "jitter_ms"),
            ("Throughput (Hz)", "throughput_hz"),
            ("Error Rate (%)", "error_rate"),
        ]

        for label, attr in metrics_to_compare:
            print(f"  {label:<20} ", end="")
            values = [getattr(results[name], attr) for name in results]
            for i, name in enumerate(results):
                val = values[i]
                if attr == "error_rate":
                    print(f"{val * 100:>11.2f}%", end=" ")
                elif attr == "throughput_hz":
                    print(f"{val:>12.1f}", end=" ")
                else:
                    print(f"{val:>12.2f}", end=" ")
            print()

        # Winner analysis
        print()
        if "serial" in results and "tcp" in results:
            serial = results["serial"]
            tcp = results["tcp"]

            rtt_diff = ((tcp.rtt_ms - serial.rtt_ms) / serial.rtt_ms * 100) if serial.rtt_ms > 0 else 0
            throughput_diff = ((serial.throughput_hz - tcp.throughput_hz) / tcp.throughput_hz * 100) if tcp.throughput_hz > 0 else 0

            if serial.rtt_ms < tcp.rtt_ms:
                print(f"  Serial has {abs(rtt_diff):.1f}% lower RTT")
            else:
                print(f"  TCP has {abs(rtt_diff):.1f}% lower RTT")

            if serial.throughput_hz > tcp.throughput_hz:
                print(f"  Serial has {abs(throughput_diff):.1f}% higher throughput")
            else:
                print(f"  TCP has {abs(throughput_diff):.1f}% higher throughput")

    # Save report
    if save_report and results:
        # Create combined result
        first_transport = list(results.keys())[0]
        first_metrics = results[first_transport]

        env = BenchmarkEnvironment.capture(
            transport="comparison",
            port_or_host=serial_port or f"{tcp_host}:{tcp_port}" or "multiple",
            baud_rate=serial_baudrate if serial_port else None,
            protocol="json",
        )

        comparison_metadata = {
            transport: {
                "send_latency_ms": m.send_latency_ms,
                "rtt_ms": m.rtt_ms,
                "rtt_p95_ms": m.rtt_p95_ms,
                "rtt_p99_ms": m.rtt_p99_ms,
                "jitter_ms": m.jitter_ms,
                "throughput_hz": m.throughput_hz,
                "error_rate": m.error_rate,
            }
            for transport, m in results.items()
        }

        combined_result = make_result(
            name="transport_comparison",
            times_ms=[first_metrics.rtt_ms],
            metadata=comparison_metadata,
        )

        report = BenchmarkReport(
            benchmark="transport_compare",
            environment=env,
            results=combined_result,
        )
        filepath = report.save()
        print(f"\n  Report saved: {filepath}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Transport Comparison Benchmark")
    parser.add_argument("--serial", "-s", help="Serial port (e.g., /dev/tty.usbserial)")
    parser.add_argument("--baudrate", "-b", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--tcp", help="TCP host:port (e.g., 192.168.4.1:3333)")
    parser.add_argument("--count", "-n", type=int, default=200, help="Iterations per test")
    parser.add_argument("--timeout", "-t", type=float, default=2.0, help="Timeout per message")
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

    if not args.serial and not tcp_host:
        parser.error("Must specify at least one transport (--serial or --tcp)")

    asyncio.run(
        run_comparison(
            serial_port=args.serial,
            serial_baudrate=args.baudrate,
            tcp_host=tcp_host,
            tcp_port=tcp_port,
            count=args.count,
            timeout=args.timeout,
            save_report=not args.no_save,
        )
    )


if __name__ == "__main__":
    main()
