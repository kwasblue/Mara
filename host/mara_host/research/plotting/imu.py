# mara_host/research/plotting/imu.py
"""IMU data visualization functions."""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


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
