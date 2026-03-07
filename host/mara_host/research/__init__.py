# mara_host/research/__init__.py
"""
Research and analysis tools for robot telemetry and control.

REQUIRES: Install with research extras: pip install mara-host[research]

Modules:
- metrics: Latency, jitter, throughput, control performance metrics
- analysis: Time series filtering, resampling, correlation, statistics
- plotting: Visualization utilities for telemetry and control
- sysid: System identification (step response, frequency response, motor params)
- simulation: Physics simulation (DC motors, differential drive, noise models)
- recording: Session recording wrappers
- replay: Session replay utilities
- experiments: Experiment runner framework

Example usage:
    from mara_host.research.metrics import analyze_session
    from mara_host.research.plotting import plot_control_loop
    from mara_host.research.sysid import identify_dc_motor_step
    from mara_host.research.simulation import DiffDriveRobot
"""

try:
    import numpy as np
    _HAS_RESEARCH_DEPS = True
except ImportError as e:
    _HAS_RESEARCH_DEPS = False
    _IMPORT_ERROR = e


def _check_research_deps():
    """Raise helpful error if research dependencies not installed."""
    if not _HAS_RESEARCH_DEPS:
        raise ImportError(
            "Research module requires research dependencies. "
            "Install with: pip install mara-host[research]\n"
            f"Missing: {_IMPORT_ERROR}"
        )


# Modules that don't require numpy (can be imported directly)
_LIGHTWEIGHT_MODULES = {
    "RecordingEventBus": "recording",
    "RecordingTransport": "recording",
    "SessionReplay": "replay",
    "replay_bus_publishes": "replay",
    "ExperimentRunner": "experiments",
    "ExperimentConfig": "experiments",
    "ExperimentResult": "experiments",
    "load_robot": "config_loader",
    "load_simulation": "config_loader",
    "SimulationConfig": "config_loader",
    "list_available_robots": "config_loader",
    "generate_config_template": "config_loader",
}

# Modules that require numpy
_HEAVY_MODULES = {
    "analyze_session": "metrics",
    "SessionMetrics": "metrics",
    "LatencyStats": "metrics",
    "JitterStats": "metrics",
    "ControlMetrics": "metrics",
    "ConnectionQuality": "metrics",
    "load_session_df": "analysis",
    "lowpass_filter": "analysis",
    "moving_average": "analysis",
    "compute_signal_stats": "analysis",
    "cross_correlation": "analysis",
    "detect_outliers_iqr": "analysis",
    "plot_time_series": "plotting",
    "plot_control_loop": "plotting",
    "plot_trajectory_2d": "plotting",
    "plot_latency_cdf": "plotting",
    "plot_imu_data": "plotting",
    "create_figure": "plotting",
    "identify_first_order_step": "sysid",
    "identify_second_order_step": "sysid",
    "identify_dc_motor_step": "sysid",
    "FirstOrderParams": "sysid",
    "SecondOrderParams": "sysid",
    "DCMotorParams": "sysid",
    "DiffDriveRobot": "simulation",
    "DiffDriveConfig": "simulation",
    "DCMotor": "simulation",
    "DCMotorConfig": "simulation",
    "SimulationRunner": "simulation",
}


def __getattr__(name: str):
    """Lazy import with dependency check for heavy modules."""
    import importlib

    if name in _LIGHTWEIGHT_MODULES:
        module = importlib.import_module(f".{_LIGHTWEIGHT_MODULES[name]}", __package__)
        return getattr(module, name)

    if name in _HEAVY_MODULES:
        _check_research_deps()
        module = importlib.import_module(f".{_HEAVY_MODULES[name]}", __package__)
        return getattr(module, name)

    raise AttributeError(f"module 'mara_host.research' has no attribute '{name}'")


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
