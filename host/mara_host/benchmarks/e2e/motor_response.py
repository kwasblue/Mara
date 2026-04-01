# mara_host/benchmarks/e2e/motor_response.py
"""
Motor response benchmark - measures time from command to observed telemetry change.

Category: End-to-end
Measures: Real motor responsiveness by observing encoder/telemetry feedback.

Usage:
    python -m mara_host.benchmarks.e2e.motor_response --port /dev/tty.usbserial --count 50
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


class MotorResponseBenchmark:
    """
    Measures end-to-end motor response time.

    Sends velocity command and measures time until telemetry shows movement.
    """

    def __init__(self, client: MaraClient, bus: EventBus) -> None:
        self._client = client
        self._bus = bus
        self._telemetry_received: Optional[asyncio.Future[float]] = None
        self._initial_velocity: float = 0.0
        self._target_velocity: float = 0.0

        # Subscribe to telemetry
        bus.subscribe("telemetry", self._on_telemetry)
        bus.subscribe("telemetry.velocity", self._on_telemetry)

    def _on_telemetry(self, msg: Dict[str, Any]) -> None:
        """Check for velocity change in telemetry."""
        if self._telemetry_received is None or self._telemetry_received.done():
            return

        # Look for velocity fields
        vx = msg.get("vx", msg.get("velocity_x", msg.get("linear_velocity")))
        if vx is None:
            return

        # Check if velocity has changed toward target
        try:
            vx_float = float(vx)
            # Consider it a response if we see movement toward target
            if abs(vx_float - self._initial_velocity) > 0.01:
                self._telemetry_received.set_result(time.perf_counter())
        except (ValueError, TypeError):
            pass

    async def measure_response_time(
        self,
        target_vx: float = 0.1,
        timeout: float = 2.0,
    ) -> tuple[Optional[float], bool]:
        """
        Measure time from velocity command to observed response.

        Args:
            target_vx: Target velocity to command
            timeout: Maximum wait time

        Returns:
            (response_time_ms, success)
        """
        loop = asyncio.get_running_loop()
        self._telemetry_received = loop.create_future()
        self._initial_velocity = 0.0
        self._target_velocity = target_vx

        # Send command
        t_send = time.perf_counter()
        ok, _ = await self._client.send_reliable(
            "CMD_SET_VEL",
            {"vx": target_vx, "omega": 0.0},
            wait_for_ack=True,
        )

        if not ok:
            return None, False

        # Wait for telemetry showing response
        try:
            t_response = await asyncio.wait_for(self._telemetry_received, timeout)
            response_ms = (t_response - t_send) * 1000.0
            return response_ms, True
        except asyncio.TimeoutError:
            return None, False
        finally:
            self._telemetry_received = None

            # Stop motor
            await self._client.send_reliable(
                "CMD_SET_VEL",
                {"vx": 0.0, "omega": 0.0},
            )

    async def run(
        self,
        count: int = 50,
        target_vx: float = 0.1,
        timeout: float = 2.0,
        delay: float = 0.5,
        warmup: int = 5,
    ) -> BenchmarkResult:
        """
        Run motor response benchmark.

        Args:
            count: Number of measurements
            target_vx: Target velocity
            timeout: Timeout per measurement
            delay: Delay between measurements
            warmup: Warmup iterations

        Returns:
            BenchmarkResult
        """
        # Warmup
        print("    Warming up...")
        for _ in range(warmup):
            await self.measure_response_time(target_vx, timeout)
            await asyncio.sleep(delay)

        times_ms: List[float] = []
        timeouts = 0

        for i in range(count):
            response_ms, ok = await self.measure_response_time(target_vx, timeout)

            if ok and response_ms is not None:
                times_ms.append(response_ms)
            else:
                timeouts += 1

            await asyncio.sleep(delay)

            if (i + 1) % 10 == 0:
                print(f"      Progress: {i + 1}/{count}")

        return make_result(
            name="motor_response_time",
            times_ms=times_ms,
            error_count=timeouts,
            metadata={
                "target_vx": target_vx,
                "measurement": "command_to_telemetry",
            },
        )


async def run_benchmark(
    port: Optional[str] = None,
    tcp_host: Optional[str] = None,
    tcp_port: int = 3333,
    count: int = 50,
    target_vx: float = 0.1,
    timeout: float = 2.0,
    delay: float = 0.5,
    save_report: bool = True,
) -> BenchmarkResult:
    """Run motor response benchmark."""
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

    print_header("Motor Response Benchmark (E2E)")
    print(f"  Transport: {transport_type}")
    print(f"  Target: {port_or_host}")
    print(f"  Target velocity: {target_vx} m/s")
    print(f"  Iterations: {count}")
    print()
    print("  NOTE: This benchmark requires a robot with working motors")
    print("        and telemetry feedback. Results may timeout if")
    print("        telemetry is not configured.")

    client = MaraClient(transport=transport, bus=bus)

    try:
        await client.start()
        if tcp_host:
            await asyncio.sleep(0.5)
        print("\n    Client connected")

        benchmark = MotorResponseBenchmark(client, bus)
        result = await benchmark.run(
            count=count,
            target_vx=target_vx,
            timeout=timeout,
            delay=delay,
        )

        print()
        print_result(result)

        if result.samples == 0:
            print()
            print("  WARNING: No successful measurements. Check that:")
            print("    1. Robot has telemetry enabled")
            print("    2. Motors are connected and armed")
            print("    3. Telemetry includes velocity fields")

        if save_report and result.samples > 0:
            env = BenchmarkEnvironment.capture(
                transport=transport_type,
                port_or_host=port_or_host,
                baud_rate=baud_rate,
                protocol="json",
            )

            report = BenchmarkReport(
                benchmark="motor_response",
                environment=env,
                results=result,
            )
            filepath = report.save()
            print(f"\n  Report saved: {filepath}")

        return result

    finally:
        # Ensure motors are stopped
        try:
            await client.send_reliable("CMD_SET_VEL", {"vx": 0.0, "omega": 0.0})
        except Exception:
            pass
        await client.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Motor Response Benchmark (E2E)")
    parser.add_argument("--port", "-p", help="Serial port")
    parser.add_argument("--tcp", help="TCP host:port")
    parser.add_argument("--count", "-n", type=int, default=50, help="Number of measurements")
    parser.add_argument("--velocity", "-v", type=float, default=0.1, help="Target velocity (m/s)")
    parser.add_argument("--timeout", "-t", type=float, default=2.0, help="Timeout per measurement")
    parser.add_argument("--delay", "-d", type=float, default=0.5, help="Delay between measurements")
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
            count=args.count,
            target_vx=args.velocity,
            timeout=args.timeout,
            delay=args.delay,
            save_report=not args.no_save,
        )
    )


if __name__ == "__main__":
    main()
