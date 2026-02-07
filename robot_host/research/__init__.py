# robot_host/research/__init__.py
"""
Research and analysis tools for robot telemetry and control.

Modules:
- metrics: Latency, jitter, throughput, control performance metrics
- analysis: Time series filtering, resampling, correlation, statistics
- plotting: Visualization utilities for telemetry and control
- sysid: System identification (step response, frequency response, motor params)
- simulation: Physics simulation (DC motors, differential drive, noise models)
- recording: Session recording wrappers
- replay: Session replay utilities
- experiments: Experiment runner framework
- benchmarks: Benchmark utilities

Example usage:
    from robot_host.research.metrics import analyze_session
    from robot_host.research.plotting import plot_control_loop
    from robot_host.research.sysid import identify_dc_motor_step
    from robot_host.research.simulation import DiffDriveRobot
"""

# Re-export commonly used items
from .metrics import (
    analyze_session,
    SessionMetrics,
    LatencyStats,
    JitterStats,
    ControlMetrics,
    ConnectionQuality,
)

from .analysis import (
    load_session_df,
    lowpass_filter,
    moving_average,
    compute_signal_stats,
    cross_correlation,
    detect_outliers_iqr,
)

from .plotting import (
    plot_time_series,
    plot_control_loop,
    plot_trajectory_2d,
    plot_latency_cdf,
    plot_imu_data,
    create_figure,
)

from .sysid import (
    identify_first_order_step,
    identify_second_order_step,
    identify_dc_motor_step,
    FirstOrderParams,
    SecondOrderParams,
    DCMotorParams,
)

from .simulation import (
    DiffDriveRobot,
    DiffDriveConfig,
    DCMotor,
    DCMotorConfig,
    SimulationRunner,
)

from .recording import RecordingEventBus, RecordingTransport
from .replay import SessionReplay, replay_bus_publishes
from .experiments import ExperimentRunner, ExperimentConfig, ExperimentResult
from .config_loader import (
    load_robot,
    load_simulation,
    SimulationConfig,
    list_available_robots,
    generate_config_template,
)

__all__ = [
    # Metrics
    "analyze_session",
    "SessionMetrics",
    "LatencyStats",
    "JitterStats",
    "ControlMetrics",
    "ConnectionQuality",
    # Analysis
    "load_session_df",
    "lowpass_filter",
    "moving_average",
    "compute_signal_stats",
    "cross_correlation",
    "detect_outliers_iqr",
    # Plotting
    "plot_time_series",
    "plot_control_loop",
    "plot_trajectory_2d",
    "plot_latency_cdf",
    "plot_imu_data",
    "create_figure",
    # System ID
    "identify_first_order_step",
    "identify_second_order_step",
    "identify_dc_motor_step",
    "FirstOrderParams",
    "SecondOrderParams",
    "DCMotorParams",
    # Simulation
    "DiffDriveRobot",
    "DiffDriveConfig",
    "DCMotor",
    "DCMotorConfig",
    "SimulationRunner",
    # Recording/Replay
    "RecordingEventBus",
    "RecordingTransport",
    "SessionReplay",
    "replay_bus_publishes",
    # Experiments
    "ExperimentRunner",
    "ExperimentConfig",
    "ExperimentResult",
    # Config
    "load_robot",
    "load_simulation",
    "SimulationConfig",
    "list_available_robots",
    "generate_config_template",
]
