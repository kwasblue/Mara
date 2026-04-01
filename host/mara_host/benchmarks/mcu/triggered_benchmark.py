# mara_host/benchmarks/mcu/triggered_benchmark.py
"""
Triggered benchmark execution from host.

Sends benchmark commands to MCU, waits for completion, and collects results.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from mara_host.benchmarks.mcu.test_catalog import (
    TestId,
    BenchState,
    BenchError,
    get_test_name,
)

if TYPE_CHECKING:
    from mara_host.transport.base import BaseTransport


@dataclass
class MCUBenchmarkResult:
    """Result from an MCU benchmark run."""

    test_id: int
    test_name: str
    state: BenchState
    error: BenchError

    # Timing in microseconds
    mean_us: int
    min_us: int
    max_us: int
    p50_us: int
    p95_us: int
    p99_us: int
    jitter_us: int
    total_us: int

    samples: int
    budget_violations: int
    throughput_hz: Optional[float] = None
    timestamp_ms: int = 0

    # Computed fields
    mean_ms: float = field(init=False)
    p99_ms: float = field(init=False)

    def __post_init__(self) -> None:
        self.mean_ms = self.mean_us / 1000.0
        self.p99_ms = self.p99_us / 1000.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCUBenchmarkResult":
        """Create from MCU response dictionary."""
        test_id = data.get("test_id", 0)
        return cls(
            test_id=test_id,
            test_name=get_test_name(test_id),
            state=BenchState(data.get("state", 0)),
            error=BenchError(data.get("error", 0)),
            mean_us=data.get("mean_us", 0),
            min_us=data.get("min_us", 0),
            max_us=data.get("max_us", 0),
            p50_us=data.get("p50_us", 0),
            p95_us=data.get("p95_us", 0),
            p99_us=data.get("p99_us", 0),
            jitter_us=data.get("jitter_us", 0),
            total_us=data.get("total_us", 0),
            samples=data.get("samples", 0),
            budget_violations=data.get("budget_violations", 0),
            throughput_hz=data.get("throughput_hz"),
            timestamp_ms=data.get("timestamp_ms", 0),
        )

    def __str__(self) -> str:
        lines = [
            f"{self.test_name} (0x{self.test_id:02X}):",
            f"  samples: {self.samples}",
            f"  mean: {self.mean_ms:.3f}ms ({self.mean_us}us)",
            f"  p50: {self.p50_us}us",
            f"  p95: {self.p95_us}us",
            f"  p99: {self.p99_us}us",
            f"  min/max: {self.min_us}/{self.max_us}us",
            f"  jitter: {self.jitter_us}us",
        ]
        if self.throughput_hz:
            lines.append(f"  throughput: {self.throughput_hz:.1f} Hz")
        if self.budget_violations > 0:
            lines.append(f"  budget_violations: {self.budget_violations}")
        return "\n".join(lines)


class TriggeredBenchmark:
    """
    Run benchmarks on the MCU from the host.

    Usage:
        async with TriggeredBenchmark(transport) as bench:
            result = await bench.run_test(TestId.LOOP_TIMING, iterations=100)
            print(result)

            # List available tests
            tests = await bench.list_tests()
            for t in tests:
                print(f"{t['name']}: {t['desc']}")
    """

    def __init__(
        self,
        transport: "BaseTransport",
        timeout_s: float = 30.0,
        poll_interval_s: float = 0.1,
    ):
        """
        Initialize triggered benchmark runner.

        Args:
            transport: Connected transport to MCU
            timeout_s: Timeout for benchmark completion
            poll_interval_s: Status poll interval
        """
        self.transport = transport
        self.timeout_s = timeout_s
        self.poll_interval_s = poll_interval_s

    async def __aenter__(self) -> "TriggeredBenchmark":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def run_test(
        self,
        test_id: TestId | int,
        iterations: int = 100,
        warmup: int = 10,
        budget_us: int = 0,
    ) -> MCUBenchmarkResult:
        """
        Run a benchmark test and wait for completion.

        Args:
            test_id: Test to run
            iterations: Number of iterations
            warmup: Warmup iterations (not timed)
            budget_us: Max time per iteration (0 = unlimited)

        Returns:
            MCUBenchmarkResult with timing statistics
        """
        # Start the benchmark
        start_resp = await self._send_command(
            "CMD_BENCH_START",
            {
                "test_id": int(test_id),
                "iterations": iterations,
                "warmup": warmup,
                "budget_us": budget_us,
            },
        )

        if not start_resp.get("ok"):
            raise RuntimeError(f"Failed to start benchmark: {start_resp}")

        # Poll for completion
        deadline = asyncio.get_event_loop().time() + self.timeout_s
        while asyncio.get_event_loop().time() < deadline:
            status = await self._send_command("CMD_BENCH_STATUS", {})

            state = BenchState(status.get("state", 0))
            if state == BenchState.COMPLETE or state == BenchState.ERROR:
                break

            await asyncio.sleep(self.poll_interval_s)

        # Get results
        results_resp = await self._send_command("CMD_BENCH_GET_RESULTS", {"max": 1})
        results = results_resp.get("results", [])

        if not results:
            raise RuntimeError("No benchmark results available")

        return MCUBenchmarkResult.from_dict(results[0])

    async def run_tests(
        self,
        test_ids: List[TestId | int],
        iterations: int = 100,
        warmup: int = 10,
    ) -> List[MCUBenchmarkResult]:
        """
        Run multiple benchmark tests sequentially.

        Args:
            test_ids: Tests to run
            iterations: Number of iterations per test
            warmup: Warmup iterations per test

        Returns:
            List of results in order
        """
        results = []
        for test_id in test_ids:
            result = await self.run_test(test_id, iterations, warmup)
            results.append(result)
        return results

    async def list_tests(self) -> List[Dict[str, Any]]:
        """
        Get list of available tests from MCU.

        Returns:
            List of test info dictionaries
        """
        resp = await self._send_command("CMD_BENCH_LIST_TESTS", {})
        return resp.get("tests", [])

    async def get_status(self) -> Dict[str, Any]:
        """Get current benchmark system status."""
        return await self._send_command("CMD_BENCH_STATUS", {})

    async def stop(self) -> None:
        """Stop all running and queued benchmarks."""
        await self._send_command("CMD_BENCH_STOP", {})

    async def run_boot_tests(self) -> None:
        """Trigger boot-time benchmark tests."""
        await self._send_command("CMD_BENCH_RUN_BOOT_TESTS", {})

    async def get_results(self, max_count: int = 8) -> List[MCUBenchmarkResult]:
        """Get result history from MCU."""
        resp = await self._send_command("CMD_BENCH_GET_RESULTS", {"max": max_count})
        results = resp.get("results", [])
        return [MCUBenchmarkResult.from_dict(r) for r in results]

    async def _send_command(
        self, cmd: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send command and wait for ACK response."""
        # This assumes transport has a send_command method
        # Adjust based on actual transport API
        if hasattr(self.transport, "send_command"):
            return await self.transport.send_command(cmd, payload)

        # Fallback for simpler transports
        import json
        message = {"cmd": cmd, **payload}
        await self.transport.write(json.dumps(message).encode() + b"\n")

        # Wait for response
        response_line = await self.transport.readline()
        return json.loads(response_line.decode())
