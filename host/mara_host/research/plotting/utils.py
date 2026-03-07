# mara_host/research/plotting/utils.py
"""Plotting utility functions."""
from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure


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
