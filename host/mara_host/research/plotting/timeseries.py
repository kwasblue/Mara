# mara_host/research/plotting/timeseries.py
"""Time series plotting functions."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from .config import create_figure


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
