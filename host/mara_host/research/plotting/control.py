# mara_host/research/plotting/control.py
"""Control loop visualization functions."""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from .config import create_figure
from ..metrics import ControlMetrics


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
