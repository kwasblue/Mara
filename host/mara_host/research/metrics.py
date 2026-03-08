# mara_host/research/metrics.py
"""
Comprehensive metrics for robot telemetry analysis.

Includes:
- Latency analysis (command-to-ack, roundtrip)
- Jitter statistics (variance, percentiles)
- Throughput metrics (messages/sec, bytes/sec)
- Control performance (tracking error, overshoot, settling time)
- Connection quality metrics
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np


# =============================================================================
# Data Loading
# =============================================================================

def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load a JSONL file into a list of dictionaries."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            # JSON parser handles whitespace; skip empty lines without strip
            if line and line[0] not in ('\n', '\r', ' ', '\t'):
                rows.append(json.loads(line))
            elif line.strip():
                rows.append(json.loads(line))
    return rows


def filter_events(rows: List[Dict], event_prefix: str) -> List[Dict]:
    """Filter rows by event prefix."""
    return [r for r in rows if str(r.get("event", "")).startswith(event_prefix)]


# =============================================================================
# Basic Metrics
# =============================================================================

def basic_metrics(jsonl_path: str) -> Dict[str, Any]:
    """Compute basic rx/tx metrics from a session log."""
    rows = load_jsonl(jsonl_path)

    rx = [r for r in rows if r.get("event") == "transport.rx"]
    tx = [r for r in rows if r.get("event") == "transport.tx"]

    return {
        "counts": {"rx": len(rx), "tx": len(tx), "total": len(rows)},
        "bytes": {
            "rx_total": sum(int(r.get("n", 0)) for r in rx),
            "tx_total": sum(int(r.get("n", 0)) for r in tx),
        },
    }


# =============================================================================
# Latency Metrics
# =============================================================================

@dataclass
class LatencyStats:
    """Statistics for latency measurements."""
    count: int = 0
    min_ms: float = float("inf")
    max_ms: float = 0.0
    mean_ms: float = 0.0
    median_ms: float = 0.0
    std_ms: float = 0.0
    p50_ms: float = 0.0
    p90_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    samples: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "min_ms": self.min_ms if self.count > 0 else None,
            "max_ms": self.max_ms if self.count > 0 else None,
            "mean_ms": self.mean_ms,
            "median_ms": self.median_ms,
            "std_ms": self.std_ms,
            "p50_ms": self.p50_ms,
            "p90_ms": self.p90_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
        }


def compute_latency_stats(latencies_ms: Sequence[float]) -> LatencyStats:
    """Compute comprehensive latency statistics."""
    if not latencies_ms:
        return LatencyStats()

    arr = np.array(latencies_ms)
    return LatencyStats(
        count=len(arr),
        min_ms=float(np.min(arr)),
        max_ms=float(np.max(arr)),
        mean_ms=float(np.mean(arr)),
        median_ms=float(np.median(arr)),
        std_ms=float(np.std(arr)),
        p50_ms=float(np.percentile(arr, 50)),
        p90_ms=float(np.percentile(arr, 90)),
        p95_ms=float(np.percentile(arr, 95)),
        p99_ms=float(np.percentile(arr, 99)),
        samples=list(latencies_ms),
    )


def command_ack_latency(rows: List[Dict]) -> LatencyStats:
    """
    Compute command-to-ack latency from logged events.

    Matches 'cmd.send' events with corresponding 'cmd.ack' by sequence number.
    """
    sends = {}  # seq -> ts_ns
    latencies = []

    for row in rows:
        event = row.get("event", "")
        ts_ns = row.get("ts_ns", 0)

        if event == "cmd.send":
            seq = row.get("seq")
            if seq is not None:
                sends[seq] = ts_ns

        elif event == "cmd.ack":
            seq = row.get("seq")
            if seq in sends:
                latency_ms = (ts_ns - sends[seq]) * 1e-6
                latencies.append(latency_ms)
                del sends[seq]

    return compute_latency_stats(latencies)


def heartbeat_roundtrip(rows: List[Dict]) -> LatencyStats:
    """
    Compute heartbeat roundtrip time.

    Matches 'heartbeat.send' with 'heartbeat.recv' events.
    """
    sends = []  # List of (ts_ns,) for sequential matching
    latencies = []

    for row in rows:
        event = row.get("event", "")
        ts_ns = row.get("ts_ns", 0)

        if event == "heartbeat.send":
            sends.append(ts_ns)
        elif event == "heartbeat.recv" and sends:
            send_ts = sends.pop(0)
            latency_ms = (ts_ns - send_ts) * 1e-6
            latencies.append(latency_ms)

    return compute_latency_stats(latencies)


# =============================================================================
# Jitter Metrics
# =============================================================================

@dataclass
class JitterStats:
    """Statistics for timing jitter."""
    count: int = 0
    mean_interval_ms: float = 0.0
    jitter_ms: float = 0.0  # Standard deviation of intervals
    jitter_max_ms: float = 0.0  # Max deviation from mean
    coefficient_of_variation: float = 0.0  # jitter / mean (normalized)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "mean_interval_ms": self.mean_interval_ms,
            "jitter_ms": self.jitter_ms,
            "jitter_max_ms": self.jitter_max_ms,
            "coefficient_of_variation": self.coefficient_of_variation,
        }


def compute_jitter(timestamps_ns: Sequence[int]) -> JitterStats:
    """
    Compute jitter from a sequence of timestamps.

    Jitter is the variation in inter-arrival times.
    """
    if len(timestamps_ns) < 2:
        return JitterStats()

    intervals_ms = []
    sorted_ts = sorted(timestamps_ns)
    for i in range(1, len(sorted_ts)):
        interval_ms = (sorted_ts[i] - sorted_ts[i - 1]) * 1e-6
        intervals_ms.append(interval_ms)

    arr = np.array(intervals_ms)
    mean = float(np.mean(arr))
    std = float(np.std(arr))

    return JitterStats(
        count=len(timestamps_ns),
        mean_interval_ms=mean,
        jitter_ms=std,
        jitter_max_ms=float(np.max(np.abs(arr - mean))),
        coefficient_of_variation=std / mean if mean > 0 else 0.0,
    )


def telemetry_jitter(rows: List[Dict], event: str = "telemetry") -> JitterStats:
    """Compute jitter for telemetry messages."""
    timestamps = [
        r.get("ts_ns", 0)
        for r in rows
        if r.get("event", "").startswith(event)
    ]
    return compute_jitter(timestamps)


# =============================================================================
# Throughput Metrics
# =============================================================================

@dataclass
class ThroughputStats:
    """Throughput statistics."""
    duration_s: float = 0.0
    total_messages: int = 0
    total_bytes: int = 0
    messages_per_sec: float = 0.0
    bytes_per_sec: float = 0.0
    kbps: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration_s": self.duration_s,
            "total_messages": self.total_messages,
            "total_bytes": self.total_bytes,
            "messages_per_sec": self.messages_per_sec,
            "bytes_per_sec": self.bytes_per_sec,
            "kbps": self.kbps,
        }


def compute_throughput(
    rows: List[Dict],
    direction: str = "rx",  # "rx", "tx", or "both"
) -> ThroughputStats:
    """Compute throughput statistics for transport events."""
    if direction == "both":
        events = [r for r in rows if r.get("event", "").startswith("transport.")]
    else:
        events = [r for r in rows if r.get("event") == f"transport.{direction}"]

    if not events:
        return ThroughputStats()

    timestamps = [e.get("ts_ns", 0) for e in events]
    if not timestamps or max(timestamps) == min(timestamps):
        return ThroughputStats()

    duration_s = (max(timestamps) - min(timestamps)) * 1e-9
    total_bytes = sum(int(e.get("n", 0)) for e in events)
    total_messages = len(events)

    return ThroughputStats(
        duration_s=duration_s,
        total_messages=total_messages,
        total_bytes=total_bytes,
        messages_per_sec=total_messages / duration_s if duration_s > 0 else 0,
        bytes_per_sec=total_bytes / duration_s if duration_s > 0 else 0,
        kbps=(total_bytes * 8 / 1000) / duration_s if duration_s > 0 else 0,
    )


# =============================================================================
# Control Performance Metrics
# =============================================================================

@dataclass
class ControlMetrics:
    """Control loop performance metrics."""
    # Tracking error
    rmse: float = 0.0  # Root mean square error
    mae: float = 0.0   # Mean absolute error
    max_error: float = 0.0

    # Step response characteristics
    rise_time_s: Optional[float] = None  # 10% to 90%
    settling_time_s: Optional[float] = None  # Within 2% of final
    overshoot_percent: Optional[float] = None
    steady_state_error: Optional[float] = None

    # Stability indicators
    oscillation_count: int = 0
    damping_ratio: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rmse": self.rmse,
            "mae": self.mae,
            "max_error": self.max_error,
            "rise_time_s": self.rise_time_s,
            "settling_time_s": self.settling_time_s,
            "overshoot_percent": self.overshoot_percent,
            "steady_state_error": self.steady_state_error,
            "oscillation_count": self.oscillation_count,
            "damping_ratio": self.damping_ratio,
        }


def compute_tracking_error(
    setpoints: Sequence[float],
    actuals: Sequence[float],
) -> Tuple[float, float, float]:
    """
    Compute tracking error metrics.

    Returns: (rmse, mae, max_error)
    """
    if len(setpoints) != len(actuals) or len(setpoints) == 0:
        return (0.0, 0.0, 0.0)

    errors = np.array(setpoints) - np.array(actuals)
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    mae = float(np.mean(np.abs(errors)))
    max_error = float(np.max(np.abs(errors)))

    return (rmse, mae, max_error)


def analyze_step_response(
    times_s: Sequence[float],
    values: Sequence[float],
    setpoint: float,
    initial: float = 0.0,
    settling_threshold: float = 0.02,  # 2% band
) -> ControlMetrics:
    """
    Analyze step response characteristics.

    Args:
        times_s: Time values in seconds
        values: Response values
        setpoint: Target setpoint value
        initial: Initial value before step
        settling_threshold: Settling band as fraction of step size
    """
    if len(times_s) < 2 or len(values) < 2:
        return ControlMetrics()

    t = np.array(times_s)
    y = np.array(values)
    step_size = setpoint - initial

    if abs(step_size) < 1e-9:
        return ControlMetrics()

    # Normalize response
    y_norm = (y - initial) / step_size

    # Find rise time (10% to 90%)
    rise_time_s = None
    t_10 = t_90 = None
    for i, yn in enumerate(y_norm):
        if t_10 is None and yn >= 0.1:
            t_10 = t[i]
        if t_90 is None and yn >= 0.9:
            t_90 = t[i]
            break
    if t_10 is not None and t_90 is not None:
        rise_time_s = float(t_90 - t_10)

    # Find overshoot
    peak = float(np.max(y_norm))
    overshoot_percent = max(0, (peak - 1.0) * 100) if peak > 1.0 else 0.0

    # Find settling time
    settling_time_s = None
    settling_band = settling_threshold
    for i in range(len(y_norm) - 1, -1, -1):
        if abs(y_norm[i] - 1.0) > settling_band:
            if i + 1 < len(t):
                settling_time_s = float(t[i + 1] - t[0])
            break

    # Steady state error
    steady_state = float(np.mean(y_norm[-max(1, len(y_norm) // 10):]))
    steady_state_error = abs(1.0 - steady_state) * abs(step_size)

    # Count oscillations (zero crossings of derivative)
    dy = np.diff(y_norm)
    sign_changes = np.sum(np.diff(np.sign(dy)) != 0)
    oscillation_count = int(sign_changes // 2)

    # Compute tracking error
    setpoints = np.full_like(y, setpoint)
    rmse, mae, max_error = compute_tracking_error(setpoints, y)

    return ControlMetrics(
        rmse=rmse,
        mae=mae,
        max_error=max_error,
        rise_time_s=rise_time_s,
        settling_time_s=settling_time_s,
        overshoot_percent=overshoot_percent,
        steady_state_error=steady_state_error,
        oscillation_count=oscillation_count,
    )


def velocity_tracking_metrics(rows: List[Dict]) -> Dict[str, ControlMetrics]:
    """
    Extract velocity tracking metrics from telemetry.

    Expects telemetry events with 'vx_ref', 'vx_act', 'omega_ref', 'omega_act'.
    """
    vx_ref, vx_act = [], []
    omega_ref, omega_act = [], []

    for row in rows:
        if row.get("event") != "telemetry":
            continue
        data = row.get("data", row)

        if "vx_ref" in data and "vx_act" in data:
            vx_ref.append(data["vx_ref"])
            vx_act.append(data["vx_act"])

        if "omega_ref" in data and "omega_act" in data:
            omega_ref.append(data["omega_ref"])
            omega_act.append(data["omega_act"])

    results = {}

    if vx_ref and vx_act:
        rmse, mae, max_e = compute_tracking_error(vx_ref, vx_act)
        results["vx"] = ControlMetrics(rmse=rmse, mae=mae, max_error=max_e)

    if omega_ref and omega_act:
        rmse, mae, max_e = compute_tracking_error(omega_ref, omega_act)
        results["omega"] = ControlMetrics(rmse=rmse, mae=mae, max_error=max_e)

    return results


# =============================================================================
# Connection Quality Metrics
# =============================================================================

@dataclass
class ConnectionQuality:
    """Connection health metrics."""
    total_duration_s: float = 0.0
    connected_duration_s: float = 0.0
    uptime_percent: float = 0.0
    disconnect_count: int = 0
    reconnect_count: int = 0
    message_loss_estimate: float = 0.0  # Based on sequence gaps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_duration_s": self.total_duration_s,
            "connected_duration_s": self.connected_duration_s,
            "uptime_percent": self.uptime_percent,
            "disconnect_count": self.disconnect_count,
            "reconnect_count": self.reconnect_count,
            "message_loss_estimate": self.message_loss_estimate,
        }


def analyze_connection_quality(rows: List[Dict]) -> ConnectionQuality:
    """Analyze connection quality from event logs."""
    if not rows:
        return ConnectionQuality()

    timestamps = [r.get("ts_ns", 0) for r in rows]
    total_duration_s = (max(timestamps) - min(timestamps)) * 1e-9 if timestamps else 0

    disconnect_count = sum(1 for r in rows if r.get("event") == "connection.lost")
    reconnect_count = sum(1 for r in rows if r.get("event") == "connection.restored")

    # Estimate connected duration (rough: total - disconnect periods)
    # This is simplified; a more accurate version would track state transitions
    connected_duration_s = total_duration_s  # Assume mostly connected

    # Estimate message loss from sequence gaps
    seqs = []
    for r in rows:
        seq = r.get("seq")
        if seq is not None:
            seqs.append(seq)

    message_loss = 0.0
    if len(seqs) > 1:
        seqs_sorted = sorted(set(seqs))
        expected = seqs_sorted[-1] - seqs_sorted[0] + 1
        actual = len(seqs_sorted)
        if expected > 0:
            message_loss = 1.0 - (actual / expected)

    return ConnectionQuality(
        total_duration_s=total_duration_s,
        connected_duration_s=connected_duration_s,
        uptime_percent=100 * connected_duration_s / total_duration_s if total_duration_s > 0 else 0,
        disconnect_count=disconnect_count,
        reconnect_count=reconnect_count,
        message_loss_estimate=message_loss,
    )


# =============================================================================
# Comprehensive Session Analysis
# =============================================================================

@dataclass
class SessionMetrics:
    """Complete metrics for a session."""
    basic: Dict[str, Any] = field(default_factory=dict)
    latency: LatencyStats = field(default_factory=LatencyStats)
    jitter: JitterStats = field(default_factory=JitterStats)
    throughput_rx: ThroughputStats = field(default_factory=ThroughputStats)
    throughput_tx: ThroughputStats = field(default_factory=ThroughputStats)
    control: Dict[str, ControlMetrics] = field(default_factory=dict)
    connection: ConnectionQuality = field(default_factory=ConnectionQuality)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "basic": self.basic,
            "latency": self.latency.to_dict(),
            "jitter": self.jitter.to_dict(),
            "throughput_rx": self.throughput_rx.to_dict(),
            "throughput_tx": self.throughput_tx.to_dict(),
            "control": {k: v.to_dict() for k, v in self.control.items()},
            "connection": self.connection.to_dict(),
        }


def analyze_session(jsonl_path: str) -> SessionMetrics:
    """
    Perform comprehensive analysis of a session log.

    Args:
        jsonl_path: Path to the JSONL session log

    Returns:
        SessionMetrics with all computed metrics
    """
    rows = load_jsonl(jsonl_path)

    return SessionMetrics(
        basic=basic_metrics(jsonl_path),
        latency=command_ack_latency(rows),
        jitter=telemetry_jitter(rows),
        throughput_rx=compute_throughput(rows, "rx"),
        throughput_tx=compute_throughput(rows, "tx"),
        control=velocity_tracking_metrics(rows),
        connection=analyze_connection_quality(rows),
    )


def compare_sessions(paths: List[str]) -> Dict[str, List[SessionMetrics]]:
    """
    Compare metrics across multiple sessions.

    Returns a dictionary with session paths as keys and metrics as values.
    """
    return {path: analyze_session(path) for path in paths}
