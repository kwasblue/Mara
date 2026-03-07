# mara_host/research/plotting/__init__.py
"""
Visualization utilities for robot telemetry and control analysis.

Includes:
- Time series plots (telemetry, IMU, encoders)
- Control loop visualization (setpoint vs actual)
- Trajectory plots (x, y, theta)
- Frequency domain plots (FFT, Bode, PSD)
- Latency and distribution plots
- Multi-panel dashboards
"""
from .config import DEFAULT_STYLE, apply_style, create_figure
from .timeseries import plot_time_series, plot_multi_series, plot_telemetry_dashboard
from .control import plot_setpoint_vs_actual, plot_control_loop, plot_step_response
from .trajectory import plot_trajectory_2d, plot_pose_trajectory
from .frequency import plot_fft, plot_psd, plot_bode
from .distribution import plot_histogram, plot_latency_cdf, plot_latency_stats
from .imu import plot_imu_data
from .utils import save_figure, show

__all__ = [
    # Config
    "DEFAULT_STYLE",
    "apply_style",
    "create_figure",
    # Time series
    "plot_time_series",
    "plot_multi_series",
    "plot_telemetry_dashboard",
    # Control
    "plot_setpoint_vs_actual",
    "plot_control_loop",
    "plot_step_response",
    # Trajectory
    "plot_trajectory_2d",
    "plot_pose_trajectory",
    # Frequency
    "plot_fft",
    "plot_psd",
    "plot_bode",
    # Distribution
    "plot_histogram",
    "plot_latency_cdf",
    "plot_latency_stats",
    # IMU
    "plot_imu_data",
    # Utils
    "save_figure",
    "show",
]
