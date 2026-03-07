# mara_host/research/plotting/frequency.py
"""Frequency domain plotting functions."""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from .config import create_figure
from ..analysis import compute_fft, compute_psd


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
