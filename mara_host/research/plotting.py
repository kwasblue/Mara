# mara_host/research/plotting.py
"""
Visualization utilities for robot telemetry and control analysis.

Includes:
- Time series plots (telemetry, IMU, encoders)
- Control loop visualization (setpoint vs actual)
- Trajectory plots (x, y, theta)
- Frequency domain plots (FFT, Bode, PSD)
- Latency and distribution plots
- Multi-panel dashboards
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.gridspec import GridSpec

from .analysis import compute_fft, compute_psd, compute_signal_stats
from .metrics import LatencyStats, ControlMetrics


# =============================================================================
# Plot Configuration
# =============================================================================

DEFAULT_STYLE = {
    "figure.figsize": (12, 6),
    "axes.grid": True,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "lines.linewidth": 1.5,
    "legend.fontsize": 10,
    "grid.alpha": 0.3,
}


def apply_style():
    """Apply default plotting style."""
    plt.rcParams.update(DEFAULT_STYLE)


def create_figure(
    rows: int = 1,
    cols: int = 1,
    figsize: Optional[Tuple[float, float]] = None,
    sharex: bool = False,
    sharey: bool = False,
) -> Tuple[Figure, Union[Axes, np.ndarray]]:
    """Create a figure with subplots."""
    if figsize is None:
        figsize = (12, 4 * rows)

    fig, axes = plt.subplots(
        rows, cols,
        figsize=figsize,
        sharex=sharex,
        sharey=sharey,
        squeeze=False,
    )

    if rows == 1 and cols == 1:
        return fig, axes[0, 0]
    elif rows == 1:
        return fig, axes[0]
    elif cols == 1:
        return fig, axes[:, 0]
    return fig, axes


# =============================================================================
# Time Series Plots
# =============================================================================

def plot_time_series(
    times: np.ndarray,
    values: np.ndarray,
    label: str = "",
    ax: Optional[Axes] = None,
    title: str = "",
    xlabel: str = "Time (s)",
    ylabel: str = "",
    color: Optional[str] = None,
    alpha: float = 1.0,
    linestyle: str = "-",
) -> Axes:
    """Plot a single time series."""
    if ax is None:
        fig, ax = create_figure()

    ax.plot(times, values, label=label, color=color, alpha=alpha, linestyle=linestyle)

    if title:
        ax.set_title(title)
    ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if label:
        ax.legend()
    ax.grid(True, alpha=0.3)

    return ax


def plot_multi_series(
    times: np.ndarray,
    series: Dict[str, np.ndarray],
    ax: Optional[Axes] = None,
    title: str = "",
    xlabel: str = "Time (s)",
    ylabel: str = "",
    colors: Optional[Dict[str, str]] = None,
) -> Axes:
    """Plot multiple time series on the same axes."""
    if ax is None:
        fig, ax = create_figure()

    colors = colors or {}

    for name, values in series.items():
        color = colors.get(name)
        ax.plot(times, values, label=name, color=color)

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, alpha=0.3)

    return ax


def plot_telemetry_dashboard(
    df: pd.DataFrame,
    columns: List[str],
    figsize: Optional[Tuple[float, float]] = None,
    title: str = "Telemetry Dashboard",
) -> Figure:
    """
    Create a dashboard of telemetry signals.

    Args:
        df: DataFrame with telemetry data (DatetimeIndex or numeric time column)
        columns: Columns to plot
        figsize: Figure size
        title: Overall title
    """
    n_plots = len(columns)
    if figsize is None:
        figsize = (14, 3 * n_plots)

    fig, axes = plt.subplots(n_plots, 1, figsize=figsize, sharex=True)
    if n_plots == 1:
        axes = [axes]

    fig.suptitle(title, fontsize=14)

    for ax, col in zip(axes, columns):
        if col in df.columns:
            ax.plot(df.index, df[col], label=col)
            ax.set_ylabel(col)
            ax.legend(loc="upper right")
            ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time")
    plt.tight_layout()

    return fig


# =============================================================================
# Control Loop Visualization
# =============================================================================

def plot_setpoint_vs_actual(
    times: np.ndarray,
    setpoint: np.ndarray,
    actual: np.ndarray,
    ax: Optional[Axes] = None,
    title: str = "Setpoint vs Actual",
    ylabel: str = "Value",
    show_error: bool = True,
) -> Axes:
    """
    Plot setpoint and actual values with optional error band.
    """
    if ax is None:
        fig, ax = create_figure()

    ax.plot(times, setpoint, "b--", label="Setpoint", linewidth=2)
    ax.plot(times, actual, "r-", label="Actual", alpha=0.8)

    if show_error:
        error = np.array(setpoint) - np.array(actual)
        ax.fill_between(
            times,
            actual - np.abs(error) * 0.1,
            actual + np.abs(error) * 0.1,
            alpha=0.2,
            color="red",
            label="Error band",
        )

    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, alpha=0.3)

    return ax


def plot_control_loop(
    times: np.ndarray,
    setpoint: np.ndarray,
    actual: np.ndarray,
    control_effort: Optional[np.ndarray] = None,
    figsize: Tuple[float, float] = (12, 8),
    title: str = "Control Loop Analysis",
) -> Figure:
    """
    Create a comprehensive control loop visualization.

    Shows setpoint/actual, error, and optionally control effort.
    """
    n_plots = 3 if control_effort is not None else 2
    fig, axes = plt.subplots(n_plots, 1, figsize=figsize, sharex=True)

    fig.suptitle(title, fontsize=14)

    # Plot 1: Setpoint vs Actual
    axes[0].plot(times, setpoint, "b--", label="Setpoint", linewidth=2)
    axes[0].plot(times, actual, "r-", label="Actual")
    axes[0].set_ylabel("Value")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Plot 2: Error
    error = np.array(setpoint) - np.array(actual)
    axes[1].plot(times, error, "g-", label="Error")
    axes[1].axhline(y=0, color="k", linestyle="--", alpha=0.5)
    axes[1].set_ylabel("Error")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Plot 3: Control effort (if provided)
    if control_effort is not None:
        axes[2].plot(times, control_effort, "m-", label="Control Effort")
        axes[2].set_ylabel("Control")
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time (s)")
    plt.tight_layout()

    return fig


def plot_step_response(
    times: np.ndarray,
    response: np.ndarray,
    setpoint: float,
    metrics: Optional[ControlMetrics] = None,
    ax: Optional[Axes] = None,
    title: str = "Step Response",
) -> Axes:
    """
    Plot step response with characteristic annotations.
    """
    if ax is None:
        fig, ax = create_figure()

    ax.plot(times, response, "b-", linewidth=2, label="Response")
    ax.axhline(y=setpoint, color="r", linestyle="--", label="Setpoint")

    # Settling band (2%)
    ax.axhline(y=setpoint * 1.02, color="g", linestyle=":", alpha=0.5)
    ax.axhline(y=setpoint * 0.98, color="g", linestyle=":", alpha=0.5)
    ax.fill_between(
        times,
        setpoint * 0.98,
        setpoint * 1.02,
        alpha=0.1,
        color="green",
        label="2% band",
    )

    # Annotate metrics if provided
    if metrics:
        text_lines = []
        if metrics.rise_time_s is not None:
            text_lines.append(f"Rise time: {metrics.rise_time_s*1000:.1f} ms")
        if metrics.settling_time_s is not None:
            text_lines.append(f"Settling: {metrics.settling_time_s*1000:.1f} ms")
        if metrics.overshoot_percent is not None:
            text_lines.append(f"Overshoot: {metrics.overshoot_percent:.1f}%")
        if metrics.steady_state_error is not None:
            text_lines.append(f"SS Error: {metrics.steady_state_error:.4f}")

        if text_lines:
            text = "\n".join(text_lines)
            ax.text(
                0.98, 0.02, text,
                transform=ax.transAxes,
                fontsize=9,
                verticalalignment="bottom",
                horizontalalignment="right",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
            )

    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Response")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

    return ax


# =============================================================================
# Trajectory Plots
# =============================================================================

def plot_trajectory_2d(
    x: np.ndarray,
    y: np.ndarray,
    ax: Optional[Axes] = None,
    title: str = "Robot Trajectory",
    show_start_end: bool = True,
    color_by_time: bool = True,
) -> Axes:
    """
    Plot 2D robot trajectory.
    """
    if ax is None:
        fig, ax = create_figure(figsize=(8, 8))

    if color_by_time and len(x) > 1:
        # Color by time progression
        colors = np.linspace(0, 1, len(x))
        scatter = ax.scatter(x, y, c=colors, cmap="viridis", s=5, alpha=0.7)
        plt.colorbar(scatter, ax=ax, label="Time progression")
    else:
        ax.plot(x, y, "b-", linewidth=1.5)

    if show_start_end and len(x) > 0:
        ax.plot(x[0], y[0], "go", markersize=10, label="Start")
        ax.plot(x[-1], y[-1], "ro", markersize=10, label="End")
        ax.legend()

    ax.set_title(title)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    return ax


def plot_pose_trajectory(
    x: np.ndarray,
    y: np.ndarray,
    theta: np.ndarray,
    ax: Optional[Axes] = None,
    arrow_spacing: int = 10,
    title: str = "Pose Trajectory",
) -> Axes:
    """
    Plot trajectory with orientation arrows.
    """
    if ax is None:
        fig, ax = create_figure(figsize=(10, 10))

    # Plot path
    ax.plot(x, y, "b-", linewidth=1, alpha=0.5)

    # Plot orientation arrows
    arrow_len = 0.1  # Arrow length in meters
    for i in range(0, len(x), arrow_spacing):
        dx = arrow_len * np.cos(theta[i])
        dy = arrow_len * np.sin(theta[i])
        ax.arrow(
            x[i], y[i], dx, dy,
            head_width=0.03,
            head_length=0.02,
            fc="red",
            ec="red",
            alpha=0.7,
        )

    ax.plot(x[0], y[0], "go", markersize=12, label="Start")
    ax.plot(x[-1], y[-1], "rs", markersize=12, label="End")

    ax.set_title(title)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_aspect("equal")
    ax.legend()
    ax.grid(True, alpha=0.3)

    return ax


# =============================================================================
# Frequency Domain Plots
# =============================================================================

def plot_fft(
    data: np.ndarray,
    sample_rate_hz: float,
    ax: Optional[Axes] = None,
    title: str = "FFT Magnitude",
    max_freq_hz: Optional[float] = None,
    log_scale: bool = False,
) -> Axes:
    """Plot FFT magnitude spectrum."""
    if ax is None:
        fig, ax = create_figure()

    freqs, mags = compute_fft(data, sample_rate_hz)

    if max_freq_hz:
        mask = freqs <= max_freq_hz
        freqs = freqs[mask]
        mags = mags[mask]

    if log_scale:
        ax.semilogy(freqs, mags)
    else:
        ax.plot(freqs, mags)

    ax.set_title(title)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude")
    ax.grid(True, alpha=0.3)

    return ax


def plot_psd(
    data: np.ndarray,
    sample_rate_hz: float,
    ax: Optional[Axes] = None,
    title: str = "Power Spectral Density",
    max_freq_hz: Optional[float] = None,
) -> Axes:
    """Plot power spectral density."""
    if ax is None:
        fig, ax = create_figure()

    freqs, psd = compute_psd(data, sample_rate_hz)

    if max_freq_hz:
        mask = freqs <= max_freq_hz
        freqs = freqs[mask]
        psd = psd[mask]

    ax.semilogy(freqs, psd)
    ax.set_title(title)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("PSD (V²/Hz)")
    ax.grid(True, alpha=0.3)

    return ax


def plot_bode(
    freqs: np.ndarray,
    magnitude_db: np.ndarray,
    phase_deg: np.ndarray,
    figsize: Tuple[float, float] = (10, 8),
    title: str = "Bode Plot",
) -> Figure:
    """
    Plot Bode diagram (magnitude and phase).
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True)

    fig.suptitle(title, fontsize=14)

    # Magnitude
    ax1.semilogx(freqs, magnitude_db)
    ax1.set_ylabel("Magnitude (dB)")
    ax1.axhline(y=0, color="k", linestyle="--", alpha=0.5)
    ax1.axhline(y=-3, color="r", linestyle=":", alpha=0.5, label="-3dB")
    ax1.grid(True, which="both", alpha=0.3)
    ax1.legend()

    # Phase
    ax2.semilogx(freqs, phase_deg)
    ax2.set_ylabel("Phase (deg)")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.axhline(y=-180, color="r", linestyle=":", alpha=0.5, label="-180°")
    ax2.grid(True, which="both", alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    return fig


# =============================================================================
# Distribution and Latency Plots
# =============================================================================

def plot_histogram(
    data: np.ndarray,
    ax: Optional[Axes] = None,
    title: str = "Distribution",
    xlabel: str = "Value",
    bins: int = 50,
    show_stats: bool = True,
) -> Axes:
    """Plot histogram with optional statistics annotation."""
    if ax is None:
        fig, ax = create_figure()

    ax.hist(data, bins=bins, edgecolor="black", alpha=0.7)

    if show_stats:
        stats = compute_signal_stats(data)
        text = (
            f"n={stats.count}\n"
            f"mean={stats.mean:.3f}\n"
            f"std={stats.std:.3f}\n"
            f"median={stats.median:.3f}"
        )
        ax.text(
            0.98, 0.98, text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="top",
            horizontalalignment="right",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        )

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    ax.grid(True, alpha=0.3)

    return ax


def plot_latency_cdf(
    latencies_ms: Sequence[float],
    ax: Optional[Axes] = None,
    title: str = "Latency CDF",
    percentiles: List[float] = [50, 90, 95, 99],
) -> Axes:
    """
    Plot cumulative distribution function of latencies.
    """
    if ax is None:
        fig, ax = create_figure()

    sorted_data = np.sort(latencies_ms)
    cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)

    ax.plot(sorted_data, cdf * 100, "b-", linewidth=2)

    # Mark percentiles
    colors = ["g", "orange", "r", "purple"]
    for p, c in zip(percentiles, colors):
        val = np.percentile(sorted_data, p)
        ax.axhline(y=p, color=c, linestyle="--", alpha=0.5)
        ax.axvline(x=val, color=c, linestyle="--", alpha=0.5)
        ax.plot(val, p, f"{c}o", markersize=8)
        ax.annotate(
            f"p{int(p)}: {val:.1f}ms",
            (val, p),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_title(title)
    ax.set_xlabel("Latency (ms)")
    ax.set_ylabel("Percentile (%)")
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)

    return ax


def plot_latency_stats(
    stats: LatencyStats,
    ax: Optional[Axes] = None,
    title: str = "Latency Distribution",
) -> Axes:
    """Plot latency statistics from a LatencyStats object."""
    if not stats.samples:
        if ax is None:
            fig, ax = create_figure()
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return ax

    return plot_latency_cdf(stats.samples, ax=ax, title=title)


# =============================================================================
# IMU Visualization
# =============================================================================

def plot_imu_data(
    times: np.ndarray,
    accel: Optional[Dict[str, np.ndarray]] = None,
    gyro: Optional[Dict[str, np.ndarray]] = None,
    figsize: Tuple[float, float] = (14, 8),
    title: str = "IMU Data",
) -> Figure:
    """
    Plot IMU accelerometer and gyroscope data.

    Args:
        times: Timestamps
        accel: Dict with 'x', 'y', 'z' accelerometer data (g)
        gyro: Dict with 'x', 'y', 'z' gyroscope data (deg/s)
    """
    n_plots = (1 if accel else 0) + (1 if gyro else 0)
    if n_plots == 0:
        raise ValueError("Must provide accel or gyro data")

    fig, axes = plt.subplots(n_plots, 1, figsize=figsize, sharex=True)
    if n_plots == 1:
        axes = [axes]

    fig.suptitle(title, fontsize=14)

    plot_idx = 0

    if accel:
        ax = axes[plot_idx]
        for axis, color in zip(["x", "y", "z"], ["r", "g", "b"]):
            if axis in accel:
                ax.plot(times, accel[axis], color, label=f"a_{axis}")
        ax.set_ylabel("Acceleration (g)")
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3)
        plot_idx += 1

    if gyro:
        ax = axes[plot_idx]
        for axis, color in zip(["x", "y", "z"], ["r", "g", "b"]):
            if axis in gyro:
                ax.plot(times, gyro[axis], color, label=f"ω_{axis}")
        ax.set_ylabel("Angular velocity (°/s)")
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time (s)")
    plt.tight_layout()

    return fig


# =============================================================================
# Utility Functions
# =============================================================================

def save_figure(
    fig: Figure,
    path: str,
    dpi: int = 150,
    tight: bool = True,
):
    """Save figure to file."""
    if tight:
        fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def show():
    """Display all figures."""
    plt.show()
