# mara_host/benchmarks/core.py
"""
Core benchmarking infrastructure for MARA platform.

Provides shared result types, timing utilities, and report generation.
"""

from __future__ import annotations

import gc
import json
import os
import statistics
import subprocess
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

# Directory for saving benchmark reports
REPORTS_DIR = Path(__file__).parent / "reports"


@dataclass
class BenchmarkResult:
    """Standard result type for all benchmarks."""

    name: str
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    jitter_ms: float
    samples: int
    throughput_hz: Optional[float] = None
    error_count: int = 0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        lines = [
            f"{self.name}:",
            f"  samples: {self.samples}",
            f"  mean: {self.mean_ms:.2f}ms",
            f"  p50: {self.p50_ms:.2f}ms",
            f"  p95: {self.p95_ms:.2f}ms",
            f"  p99: {self.p99_ms:.2f}ms",
            f"  min/max: {self.min_ms:.2f}/{self.max_ms:.2f}ms",
            f"  jitter: {self.jitter_ms:.2f}ms",
        ]
        if self.throughput_hz is not None:
            lines.append(f"  throughput: {self.throughput_hz:.1f} Hz")
        if self.error_count > 0:
            lines.append(f"  errors: {self.error_count}")
        if self.retry_count > 0:
            lines.append(f"  retries: {self.retry_count}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class BenchmarkEnvironment:
    """Environment metadata for benchmark reproducibility."""

    transport: str  # serial, tcp, can, ble
    port_or_host: str
    baud_rate: Optional[int]
    protocol: str  # json, binary
    git_sha: Optional[str]
    timestamp: str
    robot_config: Optional[str] = None

    @classmethod
    def capture(
        cls,
        transport: str,
        port_or_host: str,
        baud_rate: Optional[int] = None,
        protocol: str = "json",
        robot_config: Optional[str] = None,
    ) -> "BenchmarkEnvironment":
        """Capture current environment."""
        return cls(
            transport=transport,
            port_or_host=port_or_host,
            baud_rate=baud_rate,
            protocol=protocol,
            git_sha=get_git_sha(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            robot_config=robot_config,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class BenchmarkReport:
    """Complete benchmark report with environment and results."""

    benchmark: str
    environment: BenchmarkEnvironment
    results: BenchmarkResult

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "benchmark": self.benchmark,
            "environment": self.environment.to_dict(),
            "results": self.results.to_dict(),
        }

    def save(self, filename: Optional[str] = None) -> Path:
        """
        Save report to JSON file.

        Args:
            filename: Optional custom filename. If not provided, uses
                     {benchmark}_{timestamp}.json format.

        Returns:
            Path to saved file.
        """
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        if filename is None:
            # Use ISO format but make it filesystem-safe
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.benchmark}_{ts}.json"

        filepath = REPORTS_DIR / filename
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return filepath


# ---------------------------------------------------------------------------
# Timing utilities
# ---------------------------------------------------------------------------


def get_git_sha() -> Optional[str]:
    """Get current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def percentile(data: List[float], p: float) -> float:
    """
    Calculate percentile value.

    Args:
        data: Sorted list of values
        p: Percentile (0-100)

    Returns:
        Value at percentile
    """
    if not data:
        return 0.0
    k = (len(data) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1 if f + 1 < len(data) else f
    return data[f] + (k - f) * (data[c] - data[f])


def compute_stats(times_ms: List[float]) -> Dict[str, float]:
    """
    Compute standard statistics from timing samples.

    Args:
        times_ms: List of timing values in milliseconds

    Returns:
        Dictionary with mean, p50, p95, p99, min, max, jitter
    """
    if not times_ms:
        return {
            "mean_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "jitter_ms": 0.0,
        }

    sorted_times = sorted(times_ms)
    mean = statistics.mean(times_ms)

    return {
        "mean_ms": mean,
        "p50_ms": percentile(sorted_times, 50),
        "p95_ms": percentile(sorted_times, 95),
        "p99_ms": percentile(sorted_times, 99),
        "min_ms": min(times_ms),
        "max_ms": max(times_ms),
        "jitter_ms": statistics.stdev(times_ms) if len(times_ms) > 1 else 0.0,
    }


def make_result(
    name: str,
    times_ms: List[float],
    error_count: int = 0,
    retry_count: int = 0,
    throughput_hz: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> BenchmarkResult:
    """
    Create a BenchmarkResult from raw timing samples.

    Args:
        name: Benchmark name
        times_ms: List of timing values in milliseconds
        error_count: Number of errors encountered
        retry_count: Number of retries needed
        throughput_hz: Optional throughput measurement
        metadata: Optional additional metadata

    Returns:
        BenchmarkResult with computed statistics
    """
    stats = compute_stats(times_ms)
    return BenchmarkResult(
        name=name,
        mean_ms=stats["mean_ms"],
        p50_ms=stats["p50_ms"],
        p95_ms=stats["p95_ms"],
        p99_ms=stats["p99_ms"],
        min_ms=stats["min_ms"],
        max_ms=stats["max_ms"],
        jitter_ms=stats["jitter_ms"],
        samples=len(times_ms),
        throughput_hz=throughput_hz,
        error_count=error_count,
        retry_count=retry_count,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Benchmark execution utilities
# ---------------------------------------------------------------------------

T = TypeVar("T")


class Timer:
    """Context manager for timing code blocks."""

    def __init__(self) -> None:
        self.start_ns: int = 0
        self.end_ns: int = 0

    def __enter__(self) -> "Timer":
        self.start_ns = time.perf_counter_ns()
        return self

    def __exit__(self, *args: Any) -> None:
        self.end_ns = time.perf_counter_ns()

    @property
    def elapsed_ns(self) -> int:
        return self.end_ns - self.start_ns

    @property
    def elapsed_us(self) -> float:
        return self.elapsed_ns / 1000.0

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_ns / 1_000_000.0


def timed_loop(
    func: Callable[[], T],
    iterations: int,
    warmup: int = 10,
    disable_gc: bool = True,
) -> tuple[List[float], List[T]]:
    """
    Run a function multiple times and collect timing data.

    Args:
        func: Function to benchmark (should be fast, synchronous)
        iterations: Number of iterations to run
        warmup: Number of warmup iterations (not timed)
        disable_gc: Whether to disable GC during benchmark

    Returns:
        Tuple of (times_ms, results)
    """
    # Warmup
    for _ in range(warmup):
        func()

    if disable_gc:
        gc.disable()

    times_ms: List[float] = []
    results: List[T] = []

    try:
        for _ in range(iterations):
            start = time.perf_counter_ns()
            result = func()
            elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
            times_ms.append(elapsed_ms)
            results.append(result)
    finally:
        if disable_gc:
            gc.enable()

    return times_ms, results


async def async_timed_loop(
    func: Callable[[], Any],
    iterations: int,
    warmup: int = 10,
) -> tuple[List[float], List[Any]]:
    """
    Run an async function multiple times and collect timing data.

    Args:
        func: Async function to benchmark
        iterations: Number of iterations to run
        warmup: Number of warmup iterations (not timed)

    Returns:
        Tuple of (times_ms, results)
    """
    # Warmup
    for _ in range(warmup):
        await func()

    times_ms: List[float] = []
    results: List[Any] = []

    for _ in range(iterations):
        start = time.perf_counter_ns()
        result = await func()
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
        times_ms.append(elapsed_ms)
        results.append(result)

    return times_ms, results


# ---------------------------------------------------------------------------
# Console output utilities
# ---------------------------------------------------------------------------


def print_header(title: str, width: int = 60) -> None:
    """Print a formatted header."""
    print()
    print("=" * width)
    print(title)
    print("=" * width)


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n--- {title} ---")


def print_result(result: BenchmarkResult) -> None:
    """Print a benchmark result."""
    print(result)


def print_comparison(
    name: str,
    a_label: str,
    a_ms: float,
    b_label: str,
    b_ms: float,
) -> None:
    """Print a comparison between two measurements."""
    if b_ms > 0:
        speedup = a_ms / b_ms
        print(f"  {name}: {a_label}={a_ms:.3f}ms, {b_label}={b_ms:.3f}ms ({speedup:.1f}x)")
    else:
        print(f"  {name}: {a_label}={a_ms:.3f}ms, {b_label}={b_ms:.3f}ms")
