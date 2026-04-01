# mara_host/benchmarks/camera/frame_latency.py
"""
Camera frame latency benchmark - measures full camera pipeline performance.

Category: End-to-end
Measures: Frame fetch, decode, and callback latency.

Usage:
    python -m mara_host.benchmarks.camera.frame_latency --host 192.168.4.1 --duration 30
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from typing import List, Optional

from mara_host.benchmarks.core import (
    BenchmarkEnvironment,
    BenchmarkReport,
    BenchmarkResult,
    make_result,
    print_header,
    print_result,
    print_section,
    compute_stats,
)


@dataclass
class FrameTimings:
    """Timing breakdown for a single frame."""

    fetch_ms: float  # Time to receive bytes from network
    decode_ms: float  # Time to decode JPEG to image
    total_ms: float  # Total fetch + decode
    size_bytes: int


@dataclass
class CameraBenchmarkStats:
    """Aggregated camera benchmark statistics."""

    duration_s: float
    total_frames: int
    dropped_frames: int
    achieved_fps: float

    fetch_times_ms: List[float] = field(default_factory=list)
    decode_times_ms: List[float] = field(default_factory=list)
    total_times_ms: List[float] = field(default_factory=list)
    frame_sizes: List[int] = field(default_factory=list)

    @property
    def drop_rate_pct(self) -> float:
        total = self.total_frames + self.dropped_frames
        return (self.dropped_frames / total * 100) if total > 0 else 0


class CameraBenchmark:
    """Benchmarks ESP32-CAM frame pipeline."""

    def __init__(self, base_url: str, timeout: float = 3.0) -> None:
        """
        Initialize camera benchmark.

        Args:
            base_url: Base URL of ESP32-CAM (e.g., http://192.168.4.1)
            timeout: HTTP request timeout
        """
        self._base_url = base_url
        self._timeout = timeout

    def run(
        self,
        duration_s: float = 30.0,
        target_fps: Optional[float] = None,
    ) -> CameraBenchmarkStats:
        """
        Run camera frame latency benchmark.

        Args:
            duration_s: Test duration in seconds
            target_fps: Target FPS (None = as fast as possible)

        Returns:
            CameraBenchmarkStats with results
        """
        from mara_host.camera.client import Esp32CamClient, FrameResult

        client = Esp32CamClient(
            base_url=self._base_url,
            timeout=self._timeout,
            max_retries=1,  # Single attempt for benchmark
        )

        frame_delay = 1.0 / target_fps if target_fps else 0.0

        fetch_times: List[float] = []
        decode_times: List[float] = []
        total_times: List[float] = []
        sizes: List[int] = []
        dropped = 0

        start_time = time.perf_counter()
        frame_count = 0

        print(f"    Capturing frames for {duration_s}s...")

        try:
            while (time.perf_counter() - start_time) < duration_s:
                frame_start = time.perf_counter()

                # Fetch and time it manually
                t_fetch_start = time.perf_counter()
                result = client.get_frame_with_info()
                t_fetch_end = time.perf_counter()

                if result.success and result.frame is not None:
                    # Estimate decode time from client stats
                    # (The client already includes decode in latency_ms)
                    fetch_ms = result.latency_ms
                    decode_stats = client.stats.get_stats()

                    # Use tracked decode time if available
                    decode_ms = decode_stats.avg_decode_ms if hasattr(decode_stats, "avg_decode_ms") else 0.0

                    # Calculate total
                    total_ms = (t_fetch_end - t_fetch_start) * 1000

                    fetch_times.append(fetch_ms - decode_ms if decode_ms else fetch_ms)
                    decode_times.append(decode_ms)
                    total_times.append(total_ms)
                    sizes.append(result.size_bytes)
                    frame_count += 1
                else:
                    dropped += 1

                # Progress indicator
                if frame_count > 0 and frame_count % 100 == 0:
                    elapsed = time.perf_counter() - start_time
                    current_fps = frame_count / elapsed
                    print(f"      {frame_count} frames, {current_fps:.1f} FPS")

                # Rate limiting if target FPS specified
                if frame_delay > 0:
                    elapsed_frame = time.perf_counter() - frame_start
                    sleep_time = frame_delay - elapsed_frame
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        finally:
            client.close()

        actual_duration = time.perf_counter() - start_time
        achieved_fps = frame_count / actual_duration if actual_duration > 0 else 0

        return CameraBenchmarkStats(
            duration_s=actual_duration,
            total_frames=frame_count,
            dropped_frames=dropped,
            achieved_fps=achieved_fps,
            fetch_times_ms=fetch_times,
            decode_times_ms=decode_times,
            total_times_ms=total_times,
            frame_sizes=sizes,
        )


def run_benchmark(
    host: str,
    port: int = 80,
    duration: float = 30.0,
    target_fps: Optional[float] = None,
    timeout: float = 3.0,
    save_report: bool = True,
) -> CameraBenchmarkStats:
    """
    Run camera frame latency benchmark.

    Args:
        host: ESP32-CAM host address
        port: HTTP port (default 80)
        duration: Test duration in seconds
        target_fps: Target FPS (None = max)
        timeout: Request timeout
        save_report: Whether to save JSON report
    """
    print_header("Camera Frame Latency Benchmark")
    print(f"  Host: {host}:{port}")
    print(f"  Duration: {duration}s")
    print(f"  Target FPS: {target_fps or 'max'}")

    base_url = f"http://{host}:{port}" if port != 80 else f"http://{host}"

    benchmark = CameraBenchmark(base_url=base_url, timeout=timeout)
    stats = benchmark.run(duration_s=duration, target_fps=target_fps)

    # Print results
    print_section("Results")
    print(f"  Total frames:  {stats.total_frames}")
    print(f"  Dropped:       {stats.dropped_frames} ({stats.drop_rate_pct:.1f}%)")
    print(f"  Achieved FPS:  {stats.achieved_fps:.1f}")

    if stats.total_times_ms:
        import statistics

        print_section("Fetch Latency (network)")
        if stats.fetch_times_ms:
            fetch_stats = compute_stats(stats.fetch_times_ms)
            print(f"  Mean:  {fetch_stats['mean_ms']:.1f}ms")
            print(f"  P50:   {fetch_stats['p50_ms']:.1f}ms")
            print(f"  P95:   {fetch_stats['p95_ms']:.1f}ms")
            print(f"  P99:   {fetch_stats['p99_ms']:.1f}ms")

        print_section("Decode Latency (JPEG → image)")
        if stats.decode_times_ms and any(t > 0 for t in stats.decode_times_ms):
            decode_stats = compute_stats([t for t in stats.decode_times_ms if t > 0])
            print(f"  Mean:  {decode_stats['mean_ms']:.1f}ms")
            print(f"  P95:   {decode_stats['p95_ms']:.1f}ms")
        else:
            print("  (decode timing not available)")

        print_section("Total Frame Latency")
        total_stats = compute_stats(stats.total_times_ms)
        print(f"  Mean:  {total_stats['mean_ms']:.1f}ms")
        print(f"  P50:   {total_stats['p50_ms']:.1f}ms")
        print(f"  P95:   {total_stats['p95_ms']:.1f}ms")
        print(f"  P99:   {total_stats['p99_ms']:.1f}ms")
        print(f"  Max:   {total_stats['max_ms']:.1f}ms")

        print_section("Frame Size")
        avg_size = statistics.mean(stats.frame_sizes) if stats.frame_sizes else 0
        print(f"  Average: {avg_size / 1024:.1f} KB")
        if stats.frame_sizes:
            print(f"  Min:     {min(stats.frame_sizes) / 1024:.1f} KB")
            print(f"  Max:     {max(stats.frame_sizes) / 1024:.1f} KB")

    # Save report
    if save_report:
        env = BenchmarkEnvironment.capture(
            transport="http",
            port_or_host=f"{host}:{port}",
            baud_rate=None,
            protocol="jpeg",
        )

        result = make_result(
            name="camera_frame_latency",
            times_ms=stats.total_times_ms if stats.total_times_ms else [0],
            error_count=stats.dropped_frames,
            throughput_hz=stats.achieved_fps,
            metadata={
                "total_frames": stats.total_frames,
                "dropped_frames": stats.dropped_frames,
                "drop_rate_pct": stats.drop_rate_pct,
                "achieved_fps": stats.achieved_fps,
                "duration_s": stats.duration_s,
                "avg_size_bytes": statistics.mean(stats.frame_sizes) if stats.frame_sizes else 0,
            },
        )

        report = BenchmarkReport(
            benchmark="camera_frame_latency",
            environment=env,
            results=result,
        )
        filepath = report.save()
        print(f"\n  Report saved: {filepath}")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Camera Frame Latency Benchmark")
    parser.add_argument("--host", "-H", required=True, help="ESP32-CAM host address")
    parser.add_argument("--port", "-P", type=int, default=80, help="HTTP port")
    parser.add_argument("--duration", "-d", type=float, default=30.0, help="Test duration (seconds)")
    parser.add_argument("--fps", "-f", type=float, help="Target FPS (default: max)")
    parser.add_argument("--timeout", "-t", type=float, default=3.0, help="Request timeout")
    parser.add_argument("--no-save", action="store_true", help="Don't save report")

    args = parser.parse_args()

    run_benchmark(
        host=args.host,
        port=args.port,
        duration=args.duration,
        target_fps=args.fps,
        timeout=args.timeout,
        save_report=not args.no_save,
    )


if __name__ == "__main__":
    main()
