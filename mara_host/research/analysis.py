# mara_host/research/analysis.py
"""
Time series and signal analysis utilities for robot telemetry.

Includes:
- DataFrame-based analysis
- Signal filtering (low-pass, moving average, median)
- Resampling and interpolation
- Correlation analysis
- Statistical analysis
- Outlier detection
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from scipy import signal as scipy_signal
from scipy import stats


# =============================================================================
# DataFrame Loading and Conversion
# =============================================================================

def load_session_df(jsonl_path: str) -> pd.DataFrame:
    """
    Load a JSONL session log into a pandas DataFrame.

    Converts ts_ns to datetime and sets as index.
    """
    rows = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            # JSON parser handles whitespace; skip empty lines efficiently
            if line and line[0] not in ('\n', '\r', ' ', '\t'):
                rows.append(json.loads(line))
            elif line.strip():
                rows.append(json.loads(line))

    df = pd.DataFrame(rows)

    if "ts_ns" in df.columns:
        df["timestamp"] = pd.to_datetime(df["ts_ns"], unit="ns")
        df = df.set_index("timestamp")

    return df


def extract_telemetry_df(
    df: pd.DataFrame,
    event_filter: str = "telemetry",
    flatten: bool = True,
) -> pd.DataFrame:
    """
    Extract telemetry events and optionally flatten nested 'data' column.

    Args:
        df: Session DataFrame
        event_filter: Event type to filter
        flatten: If True, expand nested 'data' dict into columns
    """
    if "event" not in df.columns:
        return df

    telem = df[df["event"].str.startswith(event_filter, na=False)].copy()

    if flatten and "data" in telem.columns:
        # Expand the nested data dict into columns
        data_df = pd.json_normalize(telem["data"].dropna())
        data_df.index = telem.index[: len(data_df)]
        telem = pd.concat([telem.drop(columns=["data"]), data_df], axis=1)

    return telem


# =============================================================================
# Signal Filtering
# =============================================================================

def lowpass_filter(
    data: np.ndarray,
    cutoff_hz: float,
    sample_rate_hz: float,
    order: int = 2,
) -> np.ndarray:
    """
    Apply a Butterworth low-pass filter.

    Args:
        data: Input signal
        cutoff_hz: Cutoff frequency in Hz
        sample_rate_hz: Sample rate in Hz
        order: Filter order (default 2)

    Returns:
        Filtered signal
    """
    nyquist = sample_rate_hz / 2
    normalized_cutoff = cutoff_hz / nyquist

    if normalized_cutoff >= 1.0:
        return data  # Cutoff too high, return unchanged

    b, a = scipy_signal.butter(order, normalized_cutoff, btype="low")
    return scipy_signal.filtfilt(b, a, data)


def highpass_filter(
    data: np.ndarray,
    cutoff_hz: float,
    sample_rate_hz: float,
    order: int = 2,
) -> np.ndarray:
    """Apply a Butterworth high-pass filter."""
    nyquist = sample_rate_hz / 2
    normalized_cutoff = cutoff_hz / nyquist

    if normalized_cutoff <= 0.0:
        return data

    b, a = scipy_signal.butter(order, normalized_cutoff, btype="high")
    return scipy_signal.filtfilt(b, a, data)


def bandpass_filter(
    data: np.ndarray,
    low_hz: float,
    high_hz: float,
    sample_rate_hz: float,
    order: int = 2,
) -> np.ndarray:
    """Apply a Butterworth band-pass filter."""
    nyquist = sample_rate_hz / 2
    low = low_hz / nyquist
    high = high_hz / nyquist

    b, a = scipy_signal.butter(order, [low, high], btype="band")
    return scipy_signal.filtfilt(b, a, data)


def moving_average(data: np.ndarray, window: int) -> np.ndarray:
    """
    Apply a simple moving average filter.

    Args:
        data: Input signal
        window: Window size in samples

    Returns:
        Smoothed signal (same length, edges padded)
    """
    if window < 1:
        return data

    kernel = np.ones(window) / window
    return np.convolve(data, kernel, mode="same")


def exponential_moving_average(
    data: np.ndarray,
    alpha: float = 0.1,
) -> np.ndarray:
    """
    Apply exponential moving average (EMA).

    Args:
        data: Input signal
        alpha: Smoothing factor (0 < alpha <= 1). Higher = less smoothing.

    Returns:
        Smoothed signal
    """
    result = np.zeros_like(data, dtype=float)
    result[0] = data[0]

    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]

    return result


def median_filter(data: np.ndarray, window: int) -> np.ndarray:
    """
    Apply median filter (good for spike removal).

    Args:
        data: Input signal
        window: Window size (must be odd)
    """
    if window % 2 == 0:
        window += 1
    return scipy_signal.medfilt(data, kernel_size=window)


# =============================================================================
# Resampling and Interpolation
# =============================================================================

def resample_uniform(
    times: np.ndarray,
    values: np.ndarray,
    target_rate_hz: float,
    method: str = "linear",
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Resample non-uniform time series to uniform rate.

    Args:
        times: Timestamps (seconds)
        values: Signal values
        target_rate_hz: Target sample rate
        method: Interpolation method ('linear', 'cubic', 'nearest')

    Returns:
        (uniform_times, resampled_values)
    """
    if len(times) < 2:
        return times, values

    t_start = times[0]
    t_end = times[-1]
    dt = 1.0 / target_rate_hz
    n_samples = int((t_end - t_start) / dt) + 1

    uniform_times = np.linspace(t_start, t_end, n_samples)

    if method == "linear":
        resampled = np.interp(uniform_times, times, values)
    elif method == "cubic":
        from scipy.interpolate import interp1d
        f = interp1d(times, values, kind="cubic", fill_value="extrapolate")
        resampled = f(uniform_times)
    elif method == "nearest":
        from scipy.interpolate import interp1d
        f = interp1d(times, values, kind="nearest", fill_value="extrapolate")
        resampled = f(uniform_times)
    else:
        resampled = np.interp(uniform_times, times, values)

    return uniform_times, resampled


def fill_gaps(
    df: pd.DataFrame,
    max_gap_s: float = 1.0,
    method: str = "linear",
) -> pd.DataFrame:
    """
    Fill gaps in time series data by interpolation.

    Args:
        df: DataFrame with DatetimeIndex
        max_gap_s: Maximum gap size to fill (seconds)
        method: Interpolation method

    Returns:
        DataFrame with gaps filled
    """
    # Identify numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    # Interpolate with limit based on max_gap
    if isinstance(df.index, pd.DatetimeIndex):
        freq = pd.infer_freq(df.index) or "100ms"
        df_resampled = df.resample(freq).mean()
        df_resampled[numeric_cols] = df_resampled[numeric_cols].interpolate(
            method=method,
            limit_direction="both",
        )
        return df_resampled

    return df.interpolate(method=method)


# =============================================================================
# Correlation Analysis
# =============================================================================

def cross_correlation(
    x: np.ndarray,
    y: np.ndarray,
    max_lag: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute normalized cross-correlation between two signals.

    Args:
        x: First signal
        y: Second signal
        max_lag: Maximum lag to compute (default: len(x)//4)

    Returns:
        (lags, correlation_values)
    """
    if max_lag is None:
        max_lag = len(x) // 4

    # Normalize signals
    x = (x - np.mean(x)) / (np.std(x) + 1e-9)
    y = (y - np.mean(y)) / (np.std(y) + 1e-9)

    # Compute full cross-correlation
    corr = np.correlate(x, y, mode="full")
    corr = corr / len(x)

    # Extract relevant portion
    mid = len(corr) // 2
    lags = np.arange(-max_lag, max_lag + 1)
    corr_segment = corr[mid - max_lag : mid + max_lag + 1]

    return lags, corr_segment


def find_lag(x: np.ndarray, y: np.ndarray, max_lag: int = 100) -> int:
    """
    Find the lag that maximizes cross-correlation.

    Returns:
        Lag in samples (positive means y lags x)
    """
    lags, corr = cross_correlation(x, y, max_lag)
    return int(lags[np.argmax(corr)])


def autocorrelation(
    x: np.ndarray,
    max_lag: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute autocorrelation of a signal."""
    return cross_correlation(x, x, max_lag)


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Compute correlation matrix for numeric columns in DataFrame."""
    numeric = df.select_dtypes(include=[np.number])
    return numeric.corr()


# =============================================================================
# Statistical Analysis
# =============================================================================

@dataclass
class SignalStats:
    """Comprehensive statistics for a signal."""
    count: int
    mean: float
    std: float
    min: float
    max: float
    median: float
    q25: float
    q75: float
    iqr: float
    skewness: float
    kurtosis: float
    rms: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "count": self.count,
            "mean": self.mean,
            "std": self.std,
            "min": self.min,
            "max": self.max,
            "median": self.median,
            "q25": self.q25,
            "q75": self.q75,
            "iqr": self.iqr,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis,
            "rms": self.rms,
        }


def compute_signal_stats(data: np.ndarray) -> SignalStats:
    """Compute comprehensive statistics for a signal."""
    if len(data) == 0:
        return SignalStats(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    q25, median, q75 = np.percentile(data, [25, 50, 75])

    return SignalStats(
        count=len(data),
        mean=float(np.mean(data)),
        std=float(np.std(data)),
        min=float(np.min(data)),
        max=float(np.max(data)),
        median=float(median),
        q25=float(q25),
        q75=float(q75),
        iqr=float(q75 - q25),
        skewness=float(stats.skew(data)),
        kurtosis=float(stats.kurtosis(data)),
        rms=float(np.sqrt(np.mean(data ** 2))),
    )


def compute_rate(timestamps_s: np.ndarray) -> Tuple[float, float]:
    """
    Compute sample rate from timestamps.

    Returns:
        (mean_rate_hz, std_rate_hz)
    """
    if len(timestamps_s) < 2:
        return (0.0, 0.0)

    intervals = np.diff(timestamps_s)
    mean_interval = np.mean(intervals)
    std_interval = np.std(intervals)

    mean_rate = 1.0 / mean_interval if mean_interval > 0 else 0.0
    std_rate = std_interval / (mean_interval ** 2) if mean_interval > 0 else 0.0

    return (mean_rate, std_rate)


def segment_by_gaps(
    timestamps: np.ndarray,
    gap_threshold_s: float = 1.0,
) -> List[Tuple[int, int]]:
    """
    Segment data into continuous chunks based on time gaps.

    Args:
        timestamps: Timestamps in seconds
        gap_threshold_s: Minimum gap to trigger new segment

    Returns:
        List of (start_idx, end_idx) tuples for each segment
    """
    if len(timestamps) < 2:
        return [(0, len(timestamps))]

    gaps = np.diff(timestamps) > gap_threshold_s
    gap_indices = np.where(gaps)[0] + 1

    segments = []
    start = 0
    for gap_idx in gap_indices:
        segments.append((start, gap_idx))
        start = gap_idx
    segments.append((start, len(timestamps)))

    return segments


# =============================================================================
# Outlier Detection
# =============================================================================

def detect_outliers_zscore(
    data: np.ndarray,
    threshold: float = 3.0,
) -> np.ndarray:
    """
    Detect outliers using z-score method.

    Args:
        data: Input signal
        threshold: Z-score threshold (default 3.0 = 99.7% normal range)

    Returns:
        Boolean mask where True indicates outlier
    """
    z_scores = np.abs(stats.zscore(data))
    return z_scores > threshold


def detect_outliers_iqr(
    data: np.ndarray,
    factor: float = 1.5,
) -> np.ndarray:
    """
    Detect outliers using IQR method.

    Args:
        data: Input signal
        factor: IQR multiplier (1.5 = mild outliers, 3.0 = extreme)

    Returns:
        Boolean mask where True indicates outlier
    """
    q25, q75 = np.percentile(data, [25, 75])
    iqr = q75 - q25

    lower = q25 - factor * iqr
    upper = q75 + factor * iqr

    return (data < lower) | (data > upper)


def detect_outliers_mad(
    data: np.ndarray,
    threshold: float = 3.5,
) -> np.ndarray:
    """
    Detect outliers using Median Absolute Deviation (MAD).

    More robust than z-score for non-normal distributions.
    """
    median = np.median(data)
    mad = np.median(np.abs(data - median))

    if mad < 1e-9:
        return np.zeros(len(data), dtype=bool)

    modified_z = 0.6745 * (data - median) / mad
    return np.abs(modified_z) > threshold


def remove_outliers(
    data: np.ndarray,
    method: str = "iqr",
    **kwargs,
) -> np.ndarray:
    """
    Remove outliers from data.

    Args:
        data: Input signal
        method: 'zscore', 'iqr', or 'mad'
        **kwargs: Method-specific parameters

    Returns:
        Data with outliers replaced by NaN
    """
    if method == "zscore":
        mask = detect_outliers_zscore(data, **kwargs)
    elif method == "iqr":
        mask = detect_outliers_iqr(data, **kwargs)
    elif method == "mad":
        mask = detect_outliers_mad(data, **kwargs)
    else:
        raise ValueError(f"Unknown method: {method}")

    result = data.copy().astype(float)
    result[mask] = np.nan
    return result


# =============================================================================
# Derivative and Integration
# =============================================================================

def differentiate(
    times: np.ndarray,
    values: np.ndarray,
    smooth_window: int = 0,
) -> np.ndarray:
    """
    Compute numerical derivative.

    Args:
        times: Timestamps
        values: Signal values
        smooth_window: Optional smoothing window before differentiation
    """
    if smooth_window > 0:
        values = moving_average(values, smooth_window)

    dt = np.diff(times)
    dv = np.diff(values)

    # Avoid division by zero
    dt = np.where(dt < 1e-9, 1e-9, dt)

    derivative = dv / dt

    # Pad to maintain length
    return np.concatenate([[derivative[0]], derivative])


def integrate(
    times: np.ndarray,
    values: np.ndarray,
    method: str = "trapezoid",
) -> np.ndarray:
    """
    Compute cumulative integral.

    Args:
        times: Timestamps
        values: Signal values
        method: 'trapezoid' or 'rectangle'
    """
    result = np.zeros_like(values)

    if method == "trapezoid":
        for i in range(1, len(values)):
            dt = times[i] - times[i - 1]
            result[i] = result[i - 1] + 0.5 * (values[i] + values[i - 1]) * dt
    else:  # rectangle
        for i in range(1, len(values)):
            dt = times[i] - times[i - 1]
            result[i] = result[i - 1] + values[i - 1] * dt

    return result


# =============================================================================
# Frequency Domain Analysis
# =============================================================================

def compute_fft(
    data: np.ndarray,
    sample_rate_hz: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute single-sided FFT.

    Returns:
        (frequencies, magnitudes)
    """
    n = len(data)
    fft_vals = np.fft.fft(data)
    freqs = np.fft.fftfreq(n, 1.0 / sample_rate_hz)

    # Take positive frequencies only
    pos_mask = freqs >= 0
    freqs = freqs[pos_mask]
    magnitudes = np.abs(fft_vals[pos_mask]) * 2 / n

    return freqs, magnitudes


def compute_psd(
    data: np.ndarray,
    sample_rate_hz: float,
    nperseg: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute Power Spectral Density using Welch's method.

    Returns:
        (frequencies, psd)
    """
    if nperseg is None:
        nperseg = min(256, len(data))

    freqs, psd = scipy_signal.welch(data, sample_rate_hz, nperseg=nperseg)
    return freqs, psd


def find_dominant_frequency(
    data: np.ndarray,
    sample_rate_hz: float,
    min_freq_hz: float = 0.0,
    max_freq_hz: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Find the dominant frequency in a signal.

    Returns:
        (frequency_hz, magnitude)
    """
    freqs, mags = compute_fft(data, sample_rate_hz)

    if max_freq_hz is None:
        max_freq_hz = sample_rate_hz / 2

    # Mask valid frequency range
    mask = (freqs >= min_freq_hz) & (freqs <= max_freq_hz)
    freqs = freqs[mask]
    mags = mags[mask]

    if len(freqs) == 0:
        return (0.0, 0.0)

    idx = np.argmax(mags)
    return (float(freqs[idx]), float(mags[idx]))
