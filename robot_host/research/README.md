# Robot Research Module

A comprehensive research and analysis toolkit for robot telemetry, control analysis, and simulation.

## Quick Start

```python
# Load a robot from config file
from robot_host.research.config_loader import load_robot

robot = load_robot("configs/medium_robot.yaml")
robot.set_velocity(0.5, 0.1)  # vx=0.5 m/s, omega=0.1 rad/s

# Run simulation
for _ in range(1000):
    state = robot.step(0.01)  # 10ms steps
    print(f"Position: ({state['x']:.3f}, {state['y']:.3f})")
```

## Directory Structure

```
research/
├── configs/              # Robot configuration files
│   ├── small_robot.yaml  # Small indoor robot
│   ├── medium_robot.yaml # Research platform
│   ├── heavy_robot.yaml  # Outdoor heavy-duty robot
│   └── ideal_robot.yaml  # No noise (for algorithm testing)
├── examples/             # Example scripts
│   ├── 01_basic_simulation.py
│   ├── 02_control_loop_analysis.py
│   ├── 03_system_identification.py
│   ├── 04_signal_analysis.py
│   ├── 05_metrics_and_recording.py
│   ├── 06_noise_comparison.py
│   └── 07_full_pipeline.py
├── analysis.py           # Signal processing and time series
├── config_loader.py      # YAML/JSON config loading
├── experiments.py        # Experiment runner framework
├── metrics.py            # Performance metrics
├── plotting.py           # Visualization utilities
├── recording.py          # Session recording
├── replay.py             # Session replay
├── simulation.py         # Physics simulation
└── sysid.py              # System identification
```

## Modules

### Config Loader
Load robots from YAML/JSON configuration files:

```python
from robot_host.research.config_loader import load_robot, SimulationConfig

# Simple loading
robot = load_robot("configs/medium_robot.yaml")

# Full config access (for simulation)
config = SimulationConfig("configs/medium_robot.yaml")
print(config.name)
print(config.drive_config.wheel_radius)
robot = config.create_robot()
```

### Simulation
Realistic physics simulation with noise models:

```python
from robot_host.research.simulation import (
    DiffDriveRobot,
    DiffDriveConfig,
    DCMotor,
    SimulationRunner,
)

# Create robot
config = DiffDriveConfig(
    wheel_radius=0.05,
    wheel_base=0.2,
    max_linear_vel=1.0,
)
robot = DiffDriveRobot(config)

# Or use SimulationRunner for automated simulation
def my_controller(state):
    return 0.5, 0.1  # vx, omega

sim = SimulationRunner(robot, controller=my_controller, dt=0.01)
history = sim.run(duration_s=10.0)
```

### Metrics
Comprehensive telemetry analysis:

```python
from robot_host.research.metrics import analyze_session

# Analyze a recorded session
metrics = analyze_session("session.jsonl")

print(f"Latency p95: {metrics.latency.p95_ms:.1f} ms")
print(f"Jitter: {metrics.jitter.jitter_ms:.2f} ms")
print(f"Throughput: {metrics.throughput_rx.messages_per_sec:.1f} msg/s")
print(f"VX tracking RMSE: {metrics.control['vx'].rmse:.4f}")
```

### Analysis
Signal processing and statistics:

```python
from robot_host.research.analysis import (
    lowpass_filter,
    moving_average,
    compute_fft,
    detect_outliers_iqr,
    cross_correlation,
)

# Filter noisy data
filtered = lowpass_filter(data, cutoff_hz=10, sample_rate_hz=100)
smoothed = moving_average(data, window=10)

# Frequency analysis
freqs, mags = compute_fft(data, sample_rate_hz=100)

# Outlier detection
outliers = detect_outliers_iqr(data, factor=1.5)
```

### System Identification
Estimate system parameters from data:

```python
from robot_host.research.sysid import (
    identify_first_order_step,
    identify_dc_motor_step,
    fit_step_response,
)

# From step response
params = identify_first_order_step(times, response, input_amplitude=1.0)
print(f"Time constant: {params.tau} s")
print(f"DC gain: {params.K}")

# Motor parameters
motor_params = identify_dc_motor_step(times, voltage, velocity, current)
print(f"Motor constant: {motor_params.Km}")
```

### Plotting
Visualization utilities:

```python
from robot_host.research.plotting import (
    plot_trajectory_2d,
    plot_control_loop,
    plot_step_response,
    plot_latency_cdf,
    plot_imu_data,
)

# Trajectory
plot_trajectory_2d(x, y, title="Robot Path")

# Control loop analysis
fig = plot_control_loop(times, setpoint, actual, control_effort)

# Step response with metrics
plot_step_response(times, response, setpoint=1.0, metrics=metrics)
```

## Robot Configuration Format

```yaml
name: my_robot
description: My custom robot
type: diff_drive

drive:
  wheel_radius: 0.05      # meters
  wheel_base: 0.2         # meters
  robot_mass: 2.0         # kg
  max_linear_vel: 1.0     # m/s
  max_angular_vel: 3.0    # rad/s

  motor:
    R: 2.0                # Ohms
    L: 0.001              # Henries
    Kv: 0.01              # V/(rad/s)
    Kt: 0.01              # N·m/A
    J: 0.001              # kg·m²
    b: 0.0001             # N·m·s/rad
    max_voltage: 12.0
    max_current: 10.0

noise:
  imu:
    accel_std: 0.01       # g
    gyro_std: 0.001       # rad/s
  encoder:
    counts_per_rev: 1000
  ultrasonic:
    noise_std: 0.02       # meters

delay:
  mean_delay_ms: 5.0
  std_delay_ms: 2.0
  packet_loss_prob: 0.0

simulation:
  dt: 0.01                # seconds
```

## Running Examples

```bash
cd robot_host/research/examples

# Basic simulation
python 01_basic_simulation.py

# Control analysis
python 02_control_loop_analysis.py

# System ID
python 03_system_identification.py

# Signal analysis
python 04_signal_analysis.py

# Metrics and recording
python 05_metrics_and_recording.py

# Noise comparison
python 06_noise_comparison.py

# Full pipeline
python 07_full_pipeline.py
```

## Dependencies

Required:
- numpy
- scipy
- matplotlib
- pandas
- pyyaml

Optional:
- seaborn (enhanced plots)
- plotly (interactive plots)

## License

Part of the robot_host package.
