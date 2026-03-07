#!/usr/bin/env python3
"""
Example 05: Metrics and Session Recording

Demonstrates:
- Recording simulation data to JSONL
- Loading and analyzing session logs
- Computing comprehensive metrics
- Session comparison
"""
import json
import time
import numpy as np
from pathlib import Path
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mara_host.research.config_loader import load_robot
from mara_host.research.metrics import (
    analyze_session,
    SessionMetrics,
    compute_latency_stats,
    compute_jitter,
    compute_tracking_error,
    analyze_step_response,
)
from mara_host.research.plotting import plot_latency_cdf, create_figure
import matplotlib.pyplot as plt


def record_session(robot, session_name: str, duration: float, dt: float) -> str:
    """Record a simulated session to a JSONL file."""
    output_path = f"{session_name}.jsonl"
    start_time_ns = time.time_ns()

    with open(output_path, "w") as f:
        t = 0.0
        seq = 0

        while t < duration:
            current_time_ns = start_time_ns + int(t * 1e9)

            # Simulate varying velocity commands
            if t < 1.0:
                vx_cmd, omega_cmd = 0.0, 0.0
            elif t < 3.0:
                vx_cmd, omega_cmd = 0.5, 0.0
            elif t < 5.0:
                vx_cmd, omega_cmd = 0.3, 0.3
            elif t < 7.0:
                vx_cmd, omega_cmd = 0.5, -0.2
            else:
                vx_cmd, omega_cmd = 0.0, 0.0

            # Log command send event
            cmd_event = {
                "ts_ns": current_time_ns,
                "event": "cmd.send",
                "seq": seq,
                "cmd": "SET_VEL",
                "vx": vx_cmd,
                "omega": omega_cmd,
            }
            f.write(json.dumps(cmd_event) + "\n")

            # Simulate latency (3-15 ms with some jitter)
            latency_ns = int(np.random.uniform(3, 15) * 1e6)

            # Execute command
            robot.set_velocity(vx_cmd, omega_cmd)
            state = robot.step(dt)

            # Log ACK event
            ack_event = {
                "ts_ns": current_time_ns + latency_ns,
                "event": "cmd.ack",
                "seq": seq,
                "ok": True,
            }
            f.write(json.dumps(ack_event) + "\n")

            # Log telemetry event
            telem_event = {
                "ts_ns": current_time_ns + latency_ns,
                "event": "telemetry",
                "data": {
                    "x": state["x"],
                    "y": state["y"],
                    "theta": state["theta"],
                    "vx_ref": vx_cmd,
                    "vx_act": state["vx"],
                    "omega_ref": omega_cmd,
                    "omega_act": state["omega"],
                },
            }
            f.write(json.dumps(telem_event) + "\n")

            # Simulate transport events
            rx_event = {
                "ts_ns": current_time_ns + latency_ns,
                "event": "transport.rx",
                "n": 64,  # bytes
            }
            f.write(json.dumps(rx_event) + "\n")

            tx_event = {
                "ts_ns": current_time_ns,
                "event": "transport.tx",
                "n": 32,
            }
            f.write(json.dumps(tx_event) + "\n")

            t += dt
            seq += 1

    return output_path


def main():
    print("Metrics and Recording Example")
    print("=" * 50)

    config_dir = Path(__file__).parent.parent / "configs"
    robot = load_robot(config_dir / "medium_robot.yaml")

    # Record a session
    print("\nRecording simulation session...")
    session_path = record_session(robot, "test_session", duration=10.0, dt=0.02)
    print(f"Saved session to: {session_path}")

    # Analyze the session
    print("\nAnalyzing session...")
    metrics = analyze_session(session_path)

    # Print metrics summary
    print("\n" + "=" * 50)
    print("SESSION METRICS SUMMARY")
    print("=" * 50)

    print("\n📊 Basic Metrics:")
    print(f"  Total events: {metrics.basic['counts']['total']}")
    print(f"  RX events: {metrics.basic['counts']['rx']}")
    print(f"  TX events: {metrics.basic['counts']['tx']}")
    print(f"  RX bytes: {metrics.basic['bytes']['rx_total']}")
    print(f"  TX bytes: {metrics.basic['bytes']['tx_total']}")

    print("\n⏱️  Latency Metrics:")
    print(f"  Count: {metrics.latency.count}")
    if metrics.latency.count > 0:
        print(f"  Mean: {metrics.latency.mean_ms:.2f} ms")
        print(f"  Median: {metrics.latency.median_ms:.2f} ms")
        print(f"  P95: {metrics.latency.p95_ms:.2f} ms")
        print(f"  P99: {metrics.latency.p99_ms:.2f} ms")
        print(f"  Min: {metrics.latency.min_ms:.2f} ms")
        print(f"  Max: {metrics.latency.max_ms:.2f} ms")

    print("\n📈 Jitter Metrics:")
    if metrics.jitter.count > 0:
        print(f"  Mean interval: {metrics.jitter.mean_interval_ms:.2f} ms")
        print(f"  Jitter (std): {metrics.jitter.jitter_ms:.2f} ms")
        print(f"  CV: {metrics.jitter.coefficient_of_variation:.4f}")

    print("\n🚀 Throughput Metrics:")
    print(f"  RX: {metrics.throughput_rx.messages_per_sec:.1f} msg/s, {metrics.throughput_rx.kbps:.2f} kbps")
    print(f"  TX: {metrics.throughput_tx.messages_per_sec:.1f} msg/s, {metrics.throughput_tx.kbps:.2f} kbps")

    print("\n🎯 Control Metrics:")
    for name, ctrl in metrics.control.items():
        print(f"  {name}:")
        print(f"    RMSE: {ctrl.rmse:.4f}")
        print(f"    MAE: {ctrl.mae:.4f}")
        print(f"    Max error: {ctrl.max_error:.4f}")

    print("\n🔗 Connection Quality:")
    print(f"  Duration: {metrics.connection.total_duration_s:.2f} s")
    print(f"  Uptime: {metrics.connection.uptime_percent:.1f}%")
    print(f"  Message loss estimate: {metrics.connection.message_loss_estimate*100:.2f}%")

    # Create visualization
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Latency CDF
    if metrics.latency.samples:
        plot_latency_cdf(metrics.latency.samples, ax=axes[0, 0], title="Command Latency CDF")
    else:
        axes[0, 0].text(0.5, 0.5, "No latency data", ha="center", va="center")

    # Latency histogram
    if metrics.latency.samples:
        axes[0, 1].hist(metrics.latency.samples, bins=30, edgecolor="black", alpha=0.7)
        axes[0, 1].axvline(metrics.latency.mean_ms, color="r", linestyle="--", label=f"Mean: {metrics.latency.mean_ms:.1f}ms")
        axes[0, 1].axvline(metrics.latency.p95_ms, color="orange", linestyle="--", label=f"P95: {metrics.latency.p95_ms:.1f}ms")
        axes[0, 1].set_title("Latency Distribution")
        axes[0, 1].set_xlabel("Latency (ms)")
        axes[0, 1].set_ylabel("Count")
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

    # Control performance bar chart
    if metrics.control:
        names = list(metrics.control.keys())
        rmse_vals = [metrics.control[n].rmse for n in names]
        mae_vals = [metrics.control[n].mae for n in names]

        x = np.arange(len(names))
        width = 0.35

        axes[1, 0].bar(x - width/2, rmse_vals, width, label="RMSE", color="steelblue")
        axes[1, 0].bar(x + width/2, mae_vals, width, label="MAE", color="coral")
        axes[1, 0].set_title("Tracking Error by Signal")
        axes[1, 0].set_ylabel("Error")
        axes[1, 0].set_xticks(x)
        axes[1, 0].set_xticklabels(names)
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3, axis="y")

    # Throughput summary
    categories = ["RX Messages", "TX Messages", "RX Throughput", "TX Throughput"]
    values = [
        metrics.throughput_rx.messages_per_sec,
        metrics.throughput_tx.messages_per_sec,
        metrics.throughput_rx.kbps,
        metrics.throughput_tx.kbps,
    ]
    colors = ["#2ecc71", "#3498db", "#2ecc71", "#3498db"]

    bars = axes[1, 1].barh(categories, values, color=colors)
    axes[1, 1].set_title("Throughput Summary")
    axes[1, 1].set_xlabel("Value (msg/s or kbps)")
    for bar, val in zip(bars, values):
        axes[1, 1].text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                       f"{val:.1f}", va="center")
    axes[1, 1].grid(True, alpha=0.3, axis="x")

    plt.tight_layout()
    plt.savefig("05_metrics_and_recording.png", dpi=150)
    print("\nSaved plot to: 05_metrics_and_recording.png")
    plt.show()

    # Export metrics to JSON
    metrics_path = "test_session_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics.to_dict(), f, indent=2)
    print(f"\nExported metrics to: {metrics_path}")


if __name__ == "__main__":
    main()
