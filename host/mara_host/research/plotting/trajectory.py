# mara_host/research/plotting/trajectory.py
"""Trajectory plotting functions."""
from __future__ import annotations

from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from .config import create_figure


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
