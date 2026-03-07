#!/usr/bin/env python3
"""
Example 04: Signal Analysis

Demonstrates:
- Filtering noisy sensor data (low-pass, moving average, median)
- Frequency domain analysis (FFT, PSD)
- Statistical analysis
- Outlier detection
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mara_host.research.analysis import (
    lowpass_filter,
    highpass_filter,
    moving_average,
    median_filter,
    exponential_moving_average,
    compute_fft,
    compute_psd,
    compute_signal_stats,
    detect_outliers_iqr,
    detect_outliers_zscore,
    detect_outliers_mad,
    cross_correlation,
    find_lag,
)
from mara_host.research.plotting import plot_histogram, plot_fft, plot_psd


def generate_noisy_signal(duration: float, sample_rate: float):
    """Generate a synthetic noisy signal for testing."""
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples)

    # Base signal: sum of sinusoids
    signal = (
        1.0 * np.sin(2 * np.pi * 2.0 * t) +    # 2 Hz component
        0.5 * np.sin(2 * np.pi * 5.0 * t) +    # 5 Hz component
        0.2 * np.sin(2 * np.pi * 15.0 * t)     # 15 Hz noise
    )

    # Add Gaussian noise
    noise = np.random.normal(0, 0.3, n_samples)

    # Add a few outliers
    outlier_indices = np.random.choice(n_samples, size=10, replace=False)
    outliers = np.zeros(n_samples)
    outliers[outlier_indices] = np.random.uniform(-3, 3, size=10)

    noisy_signal = signal + noise + outliers

    return t, signal, noisy_signal


def main():
    print("Signal Analysis Example")
    print("=" * 50)

    # Generate test signal
    sample_rate = 100.0  # Hz
    duration = 5.0
    t, clean_signal, noisy_signal = generate_noisy_signal(duration, sample_rate)

    print(f"Generated {len(t)} samples at {sample_rate} Hz")

    # Compute statistics
    stats = compute_signal_stats(noisy_signal)
    print(f"\nSignal statistics:")
    print(f"  Mean: {stats.mean:.4f}")
    print(f"  Std: {stats.std:.4f}")
    print(f"  Min: {stats.min:.4f}")
    print(f"  Max: {stats.max:.4f}")
    print(f"  Skewness: {stats.skewness:.4f}")
    print(f"  Kurtosis: {stats.kurtosis:.4f}")

    # Apply different filters
    print("\nApplying filters...")

    filtered_lowpass = lowpass_filter(noisy_signal, cutoff_hz=10.0, sample_rate_hz=sample_rate)
    filtered_ma = moving_average(noisy_signal, window=10)
    filtered_ema = exponential_moving_average(noisy_signal, alpha=0.1)
    filtered_median = median_filter(noisy_signal, window=5)

    # Detect outliers
    outliers_iqr = detect_outliers_iqr(noisy_signal, factor=1.5)
    outliers_zscore = detect_outliers_zscore(noisy_signal, threshold=3.0)
    outliers_mad = detect_outliers_mad(noisy_signal, threshold=3.5)

    print(f"\nOutlier detection:")
    print(f"  IQR method: {np.sum(outliers_iqr)} outliers")
    print(f"  Z-score method: {np.sum(outliers_zscore)} outliers")
    print(f"  MAD method: {np.sum(outliers_mad)} outliers")

    # Frequency analysis
    freqs, magnitude = compute_fft(noisy_signal, sample_rate)
    freqs_psd, psd = compute_psd(noisy_signal, sample_rate)

    # Find dominant frequencies
    top_indices = np.argsort(magnitude)[-3:][::-1]
    print(f"\nDominant frequencies:")
    for idx in top_indices:
        if freqs[idx] > 0:
            print(f"  {freqs[idx]:.1f} Hz (magnitude: {magnitude[idx]:.3f})")

    # Cross-correlation example
    # Create a delayed version of the signal
    delay_samples = 10
    signal_delayed = np.roll(noisy_signal, delay_samples)
    detected_lag = find_lag(noisy_signal, signal_delayed, max_lag=50)
    print(f"\nCross-correlation lag detection:")
    print(f"  True delay: {delay_samples} samples")
    print(f"  Detected delay: {detected_lag} samples")

    # Create comprehensive plot
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))

    # Original vs filtered
    axes[0, 0].plot(t, noisy_signal, "b-", alpha=0.3, label="Noisy")
    axes[0, 0].plot(t, clean_signal, "k-", linewidth=2, label="Clean")
    axes[0, 0].plot(t, filtered_lowpass, "r-", linewidth=1.5, label="Low-pass")
    axes[0, 0].set_title("Signal Filtering: Low-pass")
    axes[0, 0].set_xlabel("Time (s)")
    axes[0, 0].set_ylabel("Amplitude")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # Other filters comparison
    axes[0, 1].plot(t, noisy_signal, "b-", alpha=0.3, label="Noisy")
    axes[0, 1].plot(t, filtered_ma, "g-", linewidth=1.5, label="Moving Avg")
    axes[0, 1].plot(t, filtered_median, "m-", linewidth=1.5, label="Median")
    axes[0, 1].set_title("Signal Filtering: MA and Median")
    axes[0, 1].set_xlabel("Time (s)")
    axes[0, 1].set_ylabel("Amplitude")
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # FFT
    plot_fft(noisy_signal, sample_rate, ax=axes[1, 0], title="FFT Magnitude", max_freq_hz=30)

    # PSD
    plot_psd(noisy_signal, sample_rate, ax=axes[1, 1], title="Power Spectral Density", max_freq_hz=30)

    # Outlier detection
    axes[2, 0].plot(t, noisy_signal, "b-", alpha=0.5, label="Signal")
    axes[2, 0].scatter(t[outliers_iqr], noisy_signal[outliers_iqr], c="red", s=50, label="Outliers (IQR)", zorder=5)
    axes[2, 0].set_title("Outlier Detection")
    axes[2, 0].set_xlabel("Time (s)")
    axes[2, 0].set_ylabel("Amplitude")
    axes[2, 0].legend()
    axes[2, 0].grid(True, alpha=0.3)

    # Histogram
    plot_histogram(noisy_signal, ax=axes[2, 1], title="Signal Distribution", bins=40)

    plt.tight_layout()
    plt.savefig("04_signal_analysis.png", dpi=150)
    print("\nSaved plot to: 04_signal_analysis.png")
    plt.show()


if __name__ == "__main__":
    main()
