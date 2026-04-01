# mara_host/benchmarks/e2e/servo_completion.py
"""
Servo completion benchmark - measures time for servo to reach target position.

Category: End-to-end
Measures: Servo command to completion acknowledgment time.

Usage:
    python -m mara_host.benchmarks.e2e.servo_completion --port /dev/tty.usbserial --count 20
"""

from __future__ import annotations

import argparse
import asyncio
import time
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


class ServoCompletionBenchmark:
    """
    Measures servo move completion time.

    Sends servo position command and waits for completion ACK or telemetry
    showing target reached.
    """

    def __init__(self, client: MaraClient, bus: EventBus) -> None:
        self._client = client
        self._bus = bus
        self._completion_received: Optional[asyncio.Future[float]] = None
        self._target_position: int = 0

        # Subscribe to servo-related events
        bus.subscribe("cmd.SERVO_MOVE_ACK", self._on_servo_ack)
        bus.subscribe("telemetry.servo", self._on_servo_telemetry)

    def _on_servo_ack(self, msg: Dict[str, Any]) -> None:
        """Handle servo move ACK."""
        if self._completion_received is None or self._completion_received.done():
            return

        # Check if this is a completion ACK
        if msg.get("completed") or msg.get("done"):
            self._completion_received.set_result(time.perf_counter())

    def _on_servo_telemetry(self, msg: Dict[str, Any]) -> None:
        """Check servo position in telemetry."""
        if self._completion_received is None or self._completion_received.done():
            return

        position = msg.get("position", msg.get("current_position"))
        if position is None:
            return

        # Check if we've reached target (within tolerance)
        try:
            pos_int = int(position)
            if abs(pos_int - self._target_position) < 20:  # ~20us tolerance
                self._completion_received.set_result(time.perf_counter())
        except (ValueError, TypeError):
            pass

    async def measure_completion_time(
        self,
        channel: int = 0,
        target_position: int = 1500,
        speed: int = 0,  # 0 = max speed
        timeout: float = 5.0,
    ) -> tuple[Optional[float], bool]:
        """
        Measure servo move completion time.

        Args:
            channel: Servo channel
            target_position: Target position in microseconds (typically 500-2500)
            speed: Movement speed (0 = max)
            timeout: Maximum wait time

        Returns:
            (completion_time_ms, success)
        """
        loop = asyncio.get_running_loop()
        self._completion_received = loop.create_future()
        self._target_position = target_position

        # Send servo command
        t_send = time.perf_counter()
        ok, _ = await self._client.send_reliable(
            "CMD_SERVO_MOVE",
            {
                "channel": channel,
                "position": target_position,
                "speed": speed,
            },
            wait_for_ack=True,
        )

        if not ok:
            return None, False

        # Wait for completion
        try:
            t_complete = await asyncio.wait_for(self._completion_received, timeout)
            completion_ms = (t_complete - t_send) * 1000.0
            return completion_ms, True
        except asyncio.TimeoutError:
            # Timeout might mean servo completed but we didn't get notification
            # Use the ACK time as a fallback
            return None, False
        finally:
            self._completion_received = None

    async def run(
        self,
        channel: int = 0,
        count: int = 20,
        timeout: float = 5.0,
        delay: float = 1.0,
        warmup: int = 3,
    ) -> BenchmarkResult:
        """
        Run servo completion benchmark.

        Alternates between two positions to measure round-trip servo movement.

        Args:
            channel: Servo channel
            count: Number of measurements
            timeout: Timeout per movement
            delay: Delay between movements
            warmup: Warmup iterations

        Returns:
            BenchmarkResult
        """
        pos_a = 1000  # Min position
        pos_b = 2000  # Max position

        # Warmup
        print("    Warming up...")
        for i in range(warmup):
            target = pos_a if i % 2 == 0 else pos_b
            await self.measure_completion_time(channel, target, timeout=timeout)
            await asyncio.sleep(delay)

        times_ms: List[float] = []
        timeouts = 0

        for i in range(count):
            target = pos_a if i % 2 == 0 else pos_b
            completion_ms, ok = await self.measure_completion_time(
                channel, target, timeout=timeout
            )

            if ok and completion_ms is not None:
                times_ms.append(completion_ms)
            else:
                timeouts += 1

            await asyncio.sleep(delay)

            if (i + 1) % 5 == 0:
                print(f"      Progress: {i + 1}/{count}")

        return make_result(
            name="servo_completion_time",
            times_ms=times_ms,
            error_count=timeouts,
            metadata={
                "channel": channel,
                "position_range": [pos_a, pos_b],
                "measurement": "command_to_completion",
            },
        )


async def run_benchmark(
    port: Optional[str] = None,
    tcp_host: Optional[str] = None,
    tcp_port: int = 3333,
    channel: int = 0,
    count: int = 20,
    timeout: float = 5.0,
    delay: float = 1.0,
    save_report: bool = True,
) -> BenchmarkResult:
    """Run servo completion benchmark."""
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

    print_header("Servo Completion Benchmark (E2E)")
    print(f"  Transport: {transport_type}")
    print(f"  Target: {port_or_host}")
    print(f"  Servo channel: {channel}")
    print(f"  Iterations: {count}")
    print()
    print("  NOTE: This benchmark requires a servo connected to the")
    print("        specified channel. Measures actual movement time.")

    client = MaraClient(transport=transport, bus=bus)

    try:
        await client.start()
        if tcp_host:
            await asyncio.sleep(0.5)
        print("\n    Client connected")

        benchmark = ServoCompletionBenchmark(client, bus)
        result = await benchmark.run(
            channel=channel,
            count=count,
            timeout=timeout,
            delay=delay,
        )

        print()
        print_result(result)

        if result.samples == 0:
            print()
            print("  WARNING: No successful measurements. Check that:")
            print(f"    1. Servo is connected to channel {channel}")
            print("    2. CMD_SERVO_MOVE is supported")
            print("    3. Servo completion ACKs are enabled")

        if save_report and result.samples > 0:
            env = BenchmarkEnvironment.capture(
                transport=transport_type,
                port_or_host=port_or_host,
                baud_rate=baud_rate,
                protocol="json",
            )

            report = BenchmarkReport(
                benchmark="servo_completion",
                environment=env,
                results=result,
            )
            filepath = report.save()
            print(f"\n  Report saved: {filepath}")

        return result

    finally:
        # Center servo before exit
        try:
            await client.send_reliable(
                "CMD_SERVO_MOVE",
                {"channel": channel, "position": 1500, "speed": 0},
            )
        except Exception:
            pass
        await client.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Servo Completion Benchmark (E2E)")
    parser.add_argument("--port", "-p", help="Serial port")
    parser.add_argument("--tcp", help="TCP host:port")
    parser.add_argument("--channel", "-c", type=int, default=0, help="Servo channel")
    parser.add_argument("--count", "-n", type=int, default=20, help="Number of measurements")
    parser.add_argument("--timeout", "-t", type=float, default=5.0, help="Timeout per movement")
    parser.add_argument("--delay", "-d", type=float, default=1.0, help="Delay between movements")
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

    if not args.port and not tcp_host:
        parser.error("Must specify either --port or --tcp")

    asyncio.run(
        run_benchmark(
            port=args.port,
            tcp_host=tcp_host,
            tcp_port=tcp_port,
            channel=args.channel,
            count=args.count,
            timeout=args.timeout,
            delay=args.delay,
            save_report=not args.no_save,
        )
    )


if __name__ == "__main__":
    main()
