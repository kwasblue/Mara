# mara_host/benchmarks/commands/command_rtt.py
"""
Command RTT benchmark - measures full command latency with detailed breakdown.

Category: Integration
Measures: Complete command path including encoding, transport, and ACK.

Usage:
    python -m mara_host.benchmarks.commands.command_rtt --port /dev/tty.usbserial --count 200
    python -m mara_host.benchmarks.commands.command_rtt --tcp 192.168.4.1:3333 --binary
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mara_host.core.event_bus import EventBus
from mara_host.logger import get_logger

logger = get_logger("benchmarks.command_rtt")
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
class CommandTiming:
    """Detailed timing breakdown for a single command."""

    cmd_type: str
    encode_time_us: float
    ack_wait_ms: float
    total_rtt_ms: float
    retry_count: int
    success: bool
    error: Optional[str] = None


class CommandRTTBenchmark:
    """Measures detailed command round-trip timing."""

    def __init__(self, client: MaraClient, bus: EventBus) -> None:
        self._client = client
        self._bus = bus

    async def measure_command(
        self,
        cmd_type: str,
        payload: Dict[str, Any],
        timeout: float = 2.0,
        binary: bool = False,
    ) -> CommandTiming:
        """
        Measure timing for a single command with ACK.

        Returns:
            CommandTiming with detailed breakdown
        """
        # Measure encoding time
        t_encode_start = time.perf_counter_ns()

        if binary:
            # Binary encoding path
            from mara_host.command.binary_codec import encode_binary_command

            try:
                _ = encode_binary_command(cmd_type, payload)
            except Exception:
                pass
        else:
            # JSON encoding path
            import json

            cmd_dict = {
                "kind": "cmd",
                "type": cmd_type,
                "seq": 0,
                **payload,
            }
            _ = json.dumps(cmd_dict, separators=(",", ":")).encode("utf-8")

        encode_time_us = (time.perf_counter_ns() - t_encode_start) / 1000.0

        # Measure send + ACK wait
        t_send_start = time.perf_counter_ns()

        # Get initial retry count from commander
        initial_retries = 0
        if hasattr(self._client, "commander"):
            initial_retries = getattr(self._client.commander, "_total_retries", 0)

        try:
            ok, error = await asyncio.wait_for(
                self._client.send_reliable(
                    cmd_type,
                    payload,
                    wait_for_ack=True,
                ),
                timeout=timeout + 1.0,  # Extra second beyond the ACK timeout
            )
        except asyncio.TimeoutError:
            ok, error = False, "send_reliable timed out"
            logger.warning(f"Command {cmd_type} timed out")

        t_end = time.perf_counter_ns()

        # Calculate timing (send and ack wait are combined in total_rtt)
        total_rtt_ms = (t_end - t_send_start) / 1_000_000.0
        ack_wait_ms = total_rtt_ms

        # Get retry count
        retry_count = 0
        if hasattr(self._client, "commander"):
            retry_count = getattr(self._client.commander, "_total_retries", 0) - initial_retries

        return CommandTiming(
            cmd_type=cmd_type,
            encode_time_us=encode_time_us,
            ack_wait_ms=ack_wait_ms,
            total_rtt_ms=total_rtt_ms,
            retry_count=max(0, retry_count),
            success=ok,
            error=error,
        )

    async def run(
        self,
        cmd_type: str = "CMD_HEARTBEAT",
        payload: Optional[Dict[str, Any]] = None,
        count: int = 200,
        timeout: float = 2.0,
        delay: float = 0.05,
        warmup: int = 10,
        binary: bool = False,
    ) -> tuple[BenchmarkResult, Dict[str, Any]]:
        """
        Run command RTT benchmark.

        Args:
            cmd_type: Command type to send
            payload: Command payload
            count: Number of commands to send
            timeout: Timeout per command
            delay: Delay between commands
            warmup: Warmup iterations
            binary: Use binary encoding

        Returns:
            (BenchmarkResult, detailed_metrics)
        """
        if payload is None:
            payload = {}

        # Warmup
        for _ in range(warmup):
            await self.measure_command(cmd_type, payload, timeout, binary)
            await asyncio.sleep(delay)

        timings: List[CommandTiming] = []
        total_retries = 0
        errors = 0

        # Disable GC during measurement to avoid inflating p95/p99 with GC pauses
        gc.disable()
        try:
            for i in range(count):
                timing = await self.measure_command(cmd_type, payload, timeout, binary)
                timings.append(timing)

                if timing.success:
                    total_retries += timing.retry_count
                else:
                    errors += 1

                if delay > 0:
                    await asyncio.sleep(delay)

                if (i + 1) % 50 == 0:
                    print(f"  Progress: {i + 1}/{count}")
        finally:
            gc.enable()

        # Extract successful timings
        success_rtts = [t.total_rtt_ms for t in timings if t.success]
        encode_times_us = [t.encode_time_us for t in timings]
        ack_waits = [t.ack_wait_ms for t in timings if t.success]

        result = make_result(
            name=f"command_rtt_{cmd_type.lower()}",
            times_ms=success_rtts,
            error_count=errors,
            retry_count=total_retries,
            metadata={
                "cmd_type": cmd_type,
                "encoding": "binary" if binary else "json",
            },
        )

        # Detailed metrics
        import statistics

        detailed = {
            "encode_time_us": {
                "mean": statistics.mean(encode_times_us) if encode_times_us else 0,
                "min": min(encode_times_us) if encode_times_us else 0,
                "max": max(encode_times_us) if encode_times_us else 0,
            },
            "ack_wait_ms": {
                "mean": statistics.mean(ack_waits) if ack_waits else 0,
                "min": min(ack_waits) if ack_waits else 0,
                "max": max(ack_waits) if ack_waits else 0,
            },
            "total_retries": total_retries,
            "timeout_count": errors,
            "pending_queue_depth": 0,  # Would need to sample during test
        }

        return result, detailed


async def run_benchmark(
    port: Optional[str] = None,
    tcp_host: Optional[str] = None,
    tcp_port: int = 3333,
    cmd_type: str = "CMD_NOP",
    count: int = 200,
    timeout: float = 2.0,
    delay: float = 0.05,
    warmup: int = 10,
    binary: bool = False,
    save_report: bool = True,
) -> BenchmarkResult:
    """Run command RTT benchmark."""
    bus = EventBus()

    # Create appropriate transport
    if port:
        from mara_host.transport.serial_transport import SerialTransport
        from mara_host.core._generated_config import DEFAULT_BAUD_RATE

        transport = SerialTransport(port=port)
        transport_type = "serial"
        port_or_host = port
        baud_rate = DEFAULT_BAUD_RATE
    elif tcp_host:
        from mara_host.transport.tcp_transport import AsyncTcpTransport

        transport = AsyncTcpTransport(host=tcp_host, port=tcp_port)
        transport_type = "tcp"
        port_or_host = f"{tcp_host}:{tcp_port}"
        baud_rate = None
    else:
        raise ValueError("Must specify either --port or --tcp")

    client = MaraClient(transport=transport, bus=bus)

    print_header("Command RTT Benchmark")
    print(f"  Transport: {transport_type}")
    print(f"  Target: {port_or_host}")
    print(f"  Command: {cmd_type}")
    print(f"  Encoding: {'binary' if binary else 'json'}")
    print(f"  Iterations: {count}")

    try:
        try:
            await asyncio.wait_for(client.start(), timeout=10.0)
        except asyncio.TimeoutError:
            print("\n  ERROR: Connection timed out after 10s")
            raise RuntimeError("Connection timeout")
        print("\n  Client connected, measuring command RTT...")

        benchmark = CommandRTTBenchmark(client, bus)
        result, detailed = await benchmark.run(
            cmd_type=cmd_type,
            count=count,
            timeout=timeout,
            delay=delay,
            warmup=warmup,
            binary=binary,
        )

        print()
        print_result(result)

        print_section("Detailed Metrics")
        enc = detailed["encode_time_us"]
        print(f"  Encode time: {enc['mean']:.2f}μs (min={enc['min']:.2f}, max={enc['max']:.2f})")
        ack = detailed["ack_wait_ms"]
        print(f"  ACK wait: {ack['mean']:.2f}ms (min={ack['min']:.2f}, max={ack['max']:.2f})")
        print(f"  Total retries: {detailed['total_retries']}")
        print(f"  Timeouts: {detailed['timeout_count']}")

        if save_report:
            env = BenchmarkEnvironment.capture(
                transport=transport_type,
                port_or_host=port_or_host,
                baud_rate=baud_rate,
                protocol="binary" if binary else "json",
            )
            result.metadata.update(detailed)
            report = BenchmarkReport(
                benchmark=f"command_rtt_{cmd_type.lower()}",
                environment=env,
                results=result,
            )
            filepath = report.save()
            print(f"\n  Report saved: {filepath}")

        return result

    finally:
        await client.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Command RTT Benchmark")
    parser.add_argument("--port", "-p", help="Serial port")
    parser.add_argument("--tcp", help="TCP host:port")
    parser.add_argument("--cmd", default="CMD_HEARTBEAT", help="Command type to benchmark")
    parser.add_argument("--count", "-n", type=int, default=200, help="Number of commands")
    parser.add_argument("--timeout", "-t", type=float, default=2.0, help="Timeout per command")
    parser.add_argument("--delay", "-d", type=float, default=0.05, help="Delay between commands")
    parser.add_argument("--warmup", "-w", type=int, default=10, help="Warmup iterations")
    parser.add_argument("--binary", "-b", action="store_true", help="Use binary encoding")
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
            cmd_type=args.cmd,
            count=args.count,
            timeout=args.timeout,
            delay=args.delay,
            warmup=args.warmup,
            binary=args.binary,
            save_report=not args.no_save,
        )
    )


if __name__ == "__main__":
    main()
