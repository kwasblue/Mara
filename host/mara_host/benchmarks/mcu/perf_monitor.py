# mara_host/benchmarks/mcu/perf_monitor.py
"""
MCU performance metrics monitoring via TELEM_PERF.

Provides tools for collecting and analyzing MCU performance telemetry.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mara_host.transport.base import BaseTransport


@dataclass
class PerfMetrics:
    """Snapshot of MCU performance metrics from TELEM_PERF."""

    timestamp: datetime

    # Heartbeat monitoring
    hb_count: int = 0
    hb_timeouts: int = 0
    hb_recoveries: int = 0
    hb_max_gap_ms: int = 0

    # Motion monitoring
    motion_cmds: int = 0
    motion_timeouts: int = 0
    motion_max_gap_ms: int = 0

    # Loop timing
    iterations: int = 0
    overruns: int = 0
    avg_total_us: int = 0
    peak_total_us: int = 0

    # Packet stats
    pkt_sent: int = 0
    pkt_bytes: int = 0
    pkt_dropped_sections: int = 0
    pkt_last_bytes: int = 0
    pkt_max_bytes: int = 0
    pkt_last_sections: int = 0
    pkt_max_sections: int = 0
    pkt_buffered: int = 0

    # Last fault
    last_fault: int = 0

    # Extended metrics (if available)
    jitter_violations: int = 0
    heap_free_min: int = 0
    stack_hw_ctrl: int = 0

    @classmethod
    def from_telemetry(cls, data: Dict[str, Any]) -> "PerfMetrics":
        """Create from parsed TELEM_PERF telemetry data."""
        return cls(
            timestamp=datetime.now(),
            hb_count=data.get("hb_count", 0),
            hb_timeouts=data.get("hb_timeouts", 0),
            hb_recoveries=data.get("hb_recoveries", 0),
            hb_max_gap_ms=data.get("hb_max_gap_ms", 0),
            motion_cmds=data.get("motion_cmds", 0),
            motion_timeouts=data.get("motion_timeouts", 0),
            motion_max_gap_ms=data.get("motion_max_gap_ms", 0),
            iterations=data.get("iterations", 0),
            overruns=data.get("overruns", 0),
            avg_total_us=data.get("avg_total_us", 0),
            peak_total_us=data.get("peak_total_us", 0),
            pkt_sent=data.get("pkt_sent", 0),
            pkt_bytes=data.get("pkt_bytes", 0),
            pkt_dropped_sections=data.get("pkt_dropped_sections", 0),
            pkt_last_bytes=data.get("pkt_last_bytes", 0),
            pkt_max_bytes=data.get("pkt_max_bytes", 0),
            pkt_last_sections=data.get("pkt_last_sections", 0),
            pkt_max_sections=data.get("pkt_max_sections", 0),
            pkt_buffered=data.get("pkt_buffered", 0),
            last_fault=data.get("last_fault", 0),
            jitter_violations=data.get("jitter_violations", 0),
            heap_free_min=data.get("heap_free_min", 0),
            stack_hw_ctrl=data.get("stack_hw_ctrl", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "heartbeat": {
                "count": self.hb_count,
                "timeouts": self.hb_timeouts,
                "recoveries": self.hb_recoveries,
                "max_gap_ms": self.hb_max_gap_ms,
            },
            "motion": {
                "cmds": self.motion_cmds,
                "timeouts": self.motion_timeouts,
                "max_gap_ms": self.motion_max_gap_ms,
            },
            "loop": {
                "iterations": self.iterations,
                "overruns": self.overruns,
                "avg_us": self.avg_total_us,
                "peak_us": self.peak_total_us,
            },
            "packets": {
                "sent": self.pkt_sent,
                "bytes": self.pkt_bytes,
                "dropped_sections": self.pkt_dropped_sections,
            },
            "extended": {
                "jitter_violations": self.jitter_violations,
                "heap_free_min": self.heap_free_min,
                "stack_hw_ctrl": self.stack_hw_ctrl,
            },
        }

    def __str__(self) -> str:
        lines = [
            f"MCU Performance @ {self.timestamp.strftime('%H:%M:%S')}:",
            f"  Loop: {self.avg_total_us}us avg, {self.peak_total_us}us peak",
            f"  Iterations: {self.iterations}, Overruns: {self.overruns}",
            f"  Heartbeat: {self.hb_count} count, {self.hb_timeouts} timeouts",
            f"  Packets: {self.pkt_sent} sent, {self.pkt_bytes} bytes",
        ]
        if self.jitter_violations > 0:
            lines.append(f"  Jitter violations: {self.jitter_violations}")
        if self.heap_free_min > 0:
            lines.append(f"  Heap free min: {self.heap_free_min} bytes")
        return "\n".join(lines)


@dataclass
class PerfSession:
    """A performance monitoring session with history."""

    samples: List[PerfMetrics] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def add_sample(self, metrics: PerfMetrics) -> None:
        """Add a metrics sample."""
        if not self.samples:
            self.start_time = metrics.timestamp
        self.samples.append(metrics)
        self.end_time = metrics.timestamp

    @property
    def duration_s(self) -> float:
        """Session duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def get_summary(self) -> Dict[str, Any]:
        """Compute summary statistics over the session."""
        if not self.samples:
            return {}

        avg_us_values = [s.avg_total_us for s in self.samples]
        peak_us_values = [s.peak_total_us for s in self.samples]
        overruns = [s.overruns for s in self.samples]

        return {
            "duration_s": self.duration_s,
            "sample_count": len(self.samples),
            "loop_avg_us": {
                "mean": sum(avg_us_values) / len(avg_us_values),
                "min": min(avg_us_values),
                "max": max(avg_us_values),
            },
            "loop_peak_us": {
                "mean": sum(peak_us_values) / len(peak_us_values),
                "min": min(peak_us_values),
                "max": max(peak_us_values),
            },
            "total_overruns": overruns[-1] - overruns[0] if len(overruns) > 1 else 0,
            "total_iterations": (
                self.samples[-1].iterations - self.samples[0].iterations
                if len(self.samples) > 1
                else 0
            ),
        }


class PerfMonitor:
    """
    Monitor MCU performance metrics via telemetry.

    Usage:
        async with PerfMonitor(transport) as monitor:
            # Get current metrics
            metrics = await monitor.get_perf()
            print(metrics)

            # Collect over time
            session = await monitor.collect(duration_s=10.0, interval_s=0.5)
            print(session.get_summary())
    """

    def __init__(
        self,
        transport: "BaseTransport",
        telemetry_section_id: int = 0x07,  # TELEM_PERF
    ):
        """
        Initialize performance monitor.

        Args:
            transport: Connected transport to MCU
            telemetry_section_id: Binary telemetry section ID for PERF data
        """
        self.transport = transport
        self.section_id = telemetry_section_id

    async def __aenter__(self) -> "PerfMonitor":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def get_perf(self) -> PerfMetrics:
        """
        Get current performance metrics.

        This sends a request and parses the telemetry response.
        """
        # The actual implementation depends on the transport API
        # This is a placeholder showing the expected interface
        try:
            # Try to read from telemetry stream
            if hasattr(self.transport, "get_telemetry_section"):
                data = await self.transport.get_telemetry_section(self.section_id)
                return PerfMetrics.from_telemetry(data)

            # Fallback: send diagnostics query
            if hasattr(self.transport, "send_command"):
                resp = await self.transport.send_command(
                    "CMD_MCU_DIAGNOSTICS_QUERY", {}
                )
                return PerfMetrics.from_telemetry(resp.get("perf", {}))

        except Exception:
            pass

        # Return empty metrics if unable to fetch
        return PerfMetrics(timestamp=datetime.now())

    async def collect(
        self,
        duration_s: float = 10.0,
        interval_s: float = 0.5,
    ) -> PerfSession:
        """
        Collect performance metrics over a time period.

        Args:
            duration_s: Collection duration in seconds
            interval_s: Sample interval in seconds

        Returns:
            PerfSession with collected samples
        """
        session = PerfSession()
        deadline = asyncio.get_event_loop().time() + duration_s

        while asyncio.get_event_loop().time() < deadline:
            try:
                metrics = await self.get_perf()
                session.add_sample(metrics)
            except Exception:
                pass

            await asyncio.sleep(interval_s)

        return session

    async def reset_counters(self) -> bool:
        """Reset MCU performance counters."""
        try:
            if hasattr(self.transport, "send_command"):
                resp = await self.transport.send_command("CMD_PERF_RESET", {})
                return resp.get("reset", False)
        except Exception:
            pass
        return False
