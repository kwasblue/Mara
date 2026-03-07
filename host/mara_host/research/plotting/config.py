# mara_host/research/plotting/config.py
"""Plot configuration and figure creation utilities."""
from __future__ import annotations

from typing import Optional, Tuple, Union

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes


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
