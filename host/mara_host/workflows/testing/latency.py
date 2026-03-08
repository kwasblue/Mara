# mara_host/workflows/testing/latency.py
"""
Latency profiler workflow.

Measures round-trip latency for communication.
"""

import asyncio
import time
from dataclasses import dataclass
from statistics import mean, stdev

from mara_host.workflows.base import BaseWorkflow, WorkflowResult, WorkflowState


@dataclass
class LatencyStats:
    """Latency statistics."""
    samples: int
    timeouts: int
    min_ms: float
    max_ms: float
    mean_ms: float
    std_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


class LatencyProfiler(BaseWorkflow):
    """
    Latency profiler workflow.

    Measures ping/pong round-trip time to characterize
    communication latency.

    Usage:
        profiler = LatencyProfiler(client)
        profiler.on_progress = lambda p, s: print(f"{p}%: {s}")

        result = await profiler.run(count=100)
        if result.ok:
            stats = result.data
            print(f"Mean: {stats['mean_ms']:.2f} ms")
            print(f"P99: {stats['p99_ms']:.2f} ms")
    """

    def __init__(self, client):
        super().__init__(client)

    @property
    def name(self) -> str:
        return "Latency Profiler"

    async def run(
        self,
        count: int = 100,
        delay_s: float = 0.05,
        timeout_s: float = 1.0,
    ) -> WorkflowResult:
        """
        Run latency profiling.

        Args:
            count: Number of pings to send
            delay_s: Delay between pings in seconds
            timeout_s: Timeout for each ping in seconds

        Returns:
            WorkflowResult with latency statistics
        """
        self.reset()
        self._set_state(WorkflowState.RUNNING)

        results: list[float] = []
        timeouts = 0

        try:
            self._emit_progress(0, f"Measuring latency ({count} pings)")

            for i in range(count):
                if self._check_cancelled():
                    return WorkflowResult.cancelled()

                progress = int((i / count) * 95)
                self._emit_progress(progress, f"Ping {i+1}/{count}")

                t0 = time.time()
                try:
                    ok, error = await asyncio.wait_for(
                        self._send_command("CMD_PING", {}),
                        timeout=timeout_s,
                    )
                    if ok:
                        rtt_ms = (time.time() - t0) * 1000
                        results.append(rtt_ms)
                    else:
                        timeouts += 1
                except asyncio.TimeoutError:
                    timeouts += 1

                await asyncio.sleep(delay_s)

            # Calculate statistics
            self._emit_progress(98, "Calculating statistics")

            if not results:
                return WorkflowResult.failure("No successful pings")

            stats = self._calculate_stats(results, timeouts)

            self._emit_progress(100, f"Complete: {len(results)}/{count} received")

            return WorkflowResult.success({
                "samples": stats.samples,
                "timeouts": stats.timeouts,
                "min_ms": stats.min_ms,
                "max_ms": stats.max_ms,
                "mean_ms": stats.mean_ms,
                "std_ms": stats.std_ms,
                "p50_ms": stats.p50_ms,
                "p95_ms": stats.p95_ms,
                "p99_ms": stats.p99_ms,
                "raw_samples": results,
            })

        except Exception as e:
            return WorkflowResult.failure(str(e))

    def _calculate_stats(
        self, results: list[float], timeouts: int
    ) -> LatencyStats:
        """Calculate latency statistics."""
        n = len(results)
        sorted_results = sorted(results)

        # Percentiles
        def percentile(data: list[float], p: float) -> float:
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]

        return LatencyStats(
            samples=n,
            timeouts=timeouts,
            min_ms=min(results),
            max_ms=max(results),
            mean_ms=mean(results),
            std_ms=stdev(results) if n > 1 else 0.0,
            p50_ms=percentile(sorted_results, 50),
            p95_ms=percentile(sorted_results, 95),
            p99_ms=percentile(sorted_results, 99),
        )
