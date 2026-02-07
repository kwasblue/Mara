#!/usr/bin/env python3
"""
Example 01: Basic Robot Simulation

Demonstrates:
- Loading a robot from a config file
- Running a simple simulation
- Collecting and plotting trajectory data
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from robot_host.research.config_loader import load_robot, SimulationConfig
from robot_host.research.simulation import SimulationRunner
from robot_host.research.plotting import plot_trajectory_2d, plot_time_series, create_figure


def main():
    # Get path to config file
    config_dir = Path(__file__).parent.parent / "configs"
    config_path = config_dir / "medium_robot.yaml"

    print(f"Loading robot from: {config_path}")

    # Method 1: Load just the robot
    robot = load_robot(config_path)
    print(f"Robot wheel radius: {robot.cfg.wheel_radius}m")
    print(f"Robot wheel base: {robot.cfg.wheel_base}m")

    # Method 2: Load full config for more control
    config = SimulationConfig(config_path)
    print(f"Robot name: {config.name}")
    print(f"Description: {config.description}")

    # Create simulation runner
    sim = config.create_simulation_runner()

    # Run simulation with varying velocity commands
    print("\nRunning simulation...")
    duration = 10.0  # seconds
    dt = 0.01

    times = []
    positions_x = []
    positions_y = []
    velocities = []

    t = 0.0
    while t < duration:
        # Generate velocity commands
        if t < 2.0:
            # Go straight
            vx, omega = 0.3, 0.0
        elif t < 4.0:
            # Turn left
            vx, omega = 0.2, 0.5
        elif t < 6.0:
            # Go straight
            vx, omega = 0.3, 0.0
        elif t < 8.0:
            # Turn right
            vx, omega = 0.2, -0.5
        else:
            # Stop
            vx, omega = 0.0, 0.0

        # Set velocity and step
        robot.set_velocity(vx, omega)
        state = robot.step(dt)

        # Record data
        times.append(t)
        positions_x.append(state["x"])
        positions_y.append(state["y"])
        velocities.append(state["vx"])

        t += dt

    # Plot results
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Trajectory plot
    plot_trajectory_2d(
        np.array(positions_x),
        np.array(positions_y),
        ax=axes[0],
        title=f"{config.name} Trajectory",
    )

    # Velocity plot
    plot_time_series(
        np.array(times),
        np.array(velocities),
        ax=axes[1],
        title="Linear Velocity",
        ylabel="Velocity (m/s)",
        label="vx",
    )

    plt.tight_layout()
    plt.savefig("01_basic_simulation.png", dpi=150)
    print("\nSaved plot to: 01_basic_simulation.png")
    plt.show()


if __name__ == "__main__":
    main()
