# mara_host/research/plotting/distribution.py
"""Distribution and latency plotting functions."""
from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np
from matplotlib.axes import Axes

from .config import create_figure
from ..analysis import compute_signal_stats
from ..metrics import LatencyStats


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
