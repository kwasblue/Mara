#!/usr/bin/env python3
"""
Example 06: Noise Model Comparison

Demonstrates:
- Comparing different robot configurations
- Visualizing sensor noise effects
- Running Monte Carlo simulations
- Statistical analysis of trajectory variance
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mara_host.research.config_loader import SimulationConfig
from mara_host.research.simulation import DiffDriveRobot


def run_trajectory(robot: DiffDriveRobot, duration: float, dt: float) -> Dict[str, np.ndarray]:
    """Run a fixed trajectory and collect data."""
    times = []
    positions_x = []
    positions_y = []
    thetas = []
    imu_gz = []

    robot.reset()
    t = 0.0

    while t < duration:
        # Fixed velocity command
        vx = 0.3 if t > 0.5 else 0.0
        omega = 0.2 if 1.0 < t < 3.0 else 0.0

        robot.set_velocity(vx, omega)
        state = robot.step(dt)
        imu = robot.get_imu_reading()

        times.append(t)
        positions_x.append(state["x"])
        positions_y.append(state["y"])
        thetas.append(state["theta"])
        imu_gz.append(imu["gz"])

        t += dt

    return {
        "times": np.array(times),
        "x": np.array(positions_x),
        "y": np.array(positions_y),
        "theta": np.array(thetas),
        "imu_gz": np.array(imu_gz),
    }


def monte_carlo_trajectories(config: SimulationConfig, n_runs: int, duration: float, dt: float) -> List[Dict]:
    """Run multiple trajectories to analyze variance."""
    results = []

    for i in range(n_runs):
        robot = config.create_robot()
        data = run_trajectory(robot, duration, dt)
        results.append(data)

    return results


def main():
    print("Noise Model Comparison Example")
    print("=" * 50)

    config_dir = Path(__file__).parent.parent / "configs"

    # Load different robot configurations
    configs = {
        "Ideal (no noise)": SimulationConfig(config_dir / "ideal_robot.yaml"),
        "Small Robot": SimulationConfig(config_dir / "small_robot.yaml"),
        "Medium Robot": SimulationConfig(config_dir / "medium_robot.yaml"),
        "Heavy Robot": SimulationConfig(config_dir / "heavy_robot.yaml"),
    }

    print("\nLoaded configurations:")
    for name, cfg in configs.items():
        print(f"  - {name}: {cfg.name}")

    # Single trajectory comparison
    print("\nRunning single trajectory for each config...")
    duration = 5.0
    dt = 0.01
    trajectories = {}

    for name, cfg in configs.items():
        robot = cfg.create_robot()
        trajectories[name] = run_trajectory(robot, duration, dt)

    # Monte Carlo analysis for one config
    print("\nRunning Monte Carlo analysis (50 runs) for Medium Robot...")
    n_runs = 50
    mc_results = monte_carlo_trajectories(configs["Medium Robot"], n_runs, duration, dt)

    # Analyze final position variance
    final_x = [r["x"][-1] for r in mc_results]
    final_y = [r["y"][-1] for r in mc_results]
    final_theta = [r["theta"][-1] for r in mc_results]

    print(f"\nFinal position statistics (n={n_runs}):")
    print(f"  X: mean={np.mean(final_x):.4f}, std={np.std(final_x):.4f}")
    print(f"  Y: mean={np.mean(final_y):.4f}, std={np.std(final_y):.4f}")
    print(f"  Theta: mean={np.mean(final_theta):.4f}, std={np.std(final_theta):.4f}")

    # Create visualizations
    fig = plt.figure(figsize=(16, 12))

    # Trajectory comparison
    ax1 = fig.add_subplot(2, 2, 1)
    colors = ["black", "blue", "green", "red"]
    for (name, data), color in zip(trajectories.items(), colors):
        ax1.plot(data["x"], data["y"], color=color, label=name, alpha=0.8)
        ax1.plot(data["x"][-1], data["y"][-1], "o", color=color, markersize=8)

    ax1.set_title("Trajectory Comparison (Single Run)")
    ax1.set_xlabel("X (m)")
    ax1.set_ylabel("Y (m)")
    ax1.legend(loc="upper left")
    ax1.set_aspect("equal")
    ax1.grid(True, alpha=0.3)

    # IMU noise comparison
    ax2 = fig.add_subplot(2, 2, 2)
    for (name, data), color in zip(trajectories.items(), colors):
        ax2.plot(data["times"], data["imu_gz"], color=color, label=name, alpha=0.7)

    ax2.set_title("IMU Gyroscope Reading (Z-axis)")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Angular velocity (rad/s)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Monte Carlo trajectories
    ax3 = fig.add_subplot(2, 2, 3)
    for i, result in enumerate(mc_results):
        alpha = 0.2 if i < n_runs - 1 else 1.0
        linewidth = 0.5 if i < n_runs - 1 else 2.0
        color = "blue" if i < n_runs - 1 else "red"
        label = None if i < n_runs - 1 else "Last run"
        ax3.plot(result["x"], result["y"], color=color, alpha=alpha, linewidth=linewidth, label=label)

    # Add mean trajectory
    mean_x = np.mean([r["x"] for r in mc_results], axis=0)
    mean_y = np.mean([r["y"] for r in mc_results], axis=0)
    ax3.plot(mean_x, mean_y, "g--", linewidth=2, label="Mean trajectory")

    ax3.set_title(f"Monte Carlo Trajectories (n={n_runs})")
    ax3.set_xlabel("X (m)")
    ax3.set_ylabel("Y (m)")
    ax3.legend()
    ax3.set_aspect("equal")
    ax3.grid(True, alpha=0.3)

    # Final position scatter plot
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.scatter(final_x, final_y, alpha=0.6, s=30)
    ax4.scatter(np.mean(final_x), np.mean(final_y), c="red", s=100, marker="x", label="Mean")

    # Draw confidence ellipse (2 std)
    from matplotlib.patches import Ellipse
    cov = np.cov(final_x, final_y)
    eigenvalues, eigenvectors = np.linalg.eig(cov)
    angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
    ellipse = Ellipse(
        (np.mean(final_x), np.mean(final_y)),
        width=2 * 2 * np.sqrt(eigenvalues[0]),
        height=2 * 2 * np.sqrt(eigenvalues[1]),
        angle=angle,
        fill=False,
        color="red",
        linestyle="--",
        label="2σ ellipse",
    )
    ax4.add_patch(ellipse)

    ax4.set_title("Final Position Distribution")
    ax4.set_xlabel("X (m)")
    ax4.set_ylabel("Y (m)")
    ax4.legend()
    ax4.set_aspect("equal")
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("06_noise_comparison.png", dpi=150)
    print("\nSaved plot to: 06_noise_comparison.png")
    plt.show()


if __name__ == "__main__":
    main()
