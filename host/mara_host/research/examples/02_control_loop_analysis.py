#!/usr/bin/env python3
"""
Example 02: Control Loop Analysis

Demonstrates:
- Implementing a simple PID velocity controller
- Analyzing step response
- Computing control metrics (rise time, overshoot, settling time)
- Visualizing control loop performance
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mara_host.research.config_loader import load_robot
from mara_host.research.metrics import analyze_step_response, ControlMetrics
from mara_host.research.plotting import plot_step_response, plot_control_loop


@dataclass
class PIDController:
    """Simple PID controller."""
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0
    integral_limit: float = 10.0

    def __post_init__(self):
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, setpoint: float, measured: float, dt: float) -> float:
        error = setpoint - measured

        # Proportional
        p_term = self.kp * error

        # Integral with anti-windup
        self.integral += error * dt
        self.integral = np.clip(self.integral, -self.integral_limit, self.integral_limit)
        i_term = self.ki * self.integral

        # Derivative
        d_term = self.kd * (error - self.prev_error) / dt if dt > 0 else 0.0
        self.prev_error = error

        return p_term + i_term + d_term


def run_step_response_test(robot, pid, setpoint, duration, dt):
    """Run a step response test and collect data."""
    times = []
    setpoints = []
    actuals = []
    controls = []

    t = 0.0
    robot.reset()
    pid.reset()

    while t < duration:
        # Step input after 0.5 seconds
        sp = setpoint if t >= 0.5 else 0.0

        # PID control
        control = pid.update(sp, robot.vx, dt)
        control = np.clip(control, -1.0, 1.0)  # Normalize to [-1, 1]

        # Apply control (convert to velocity command)
        robot.set_velocity(control * robot.cfg.max_linear_vel, 0.0)
        state = robot.step(dt)

        times.append(t)
        setpoints.append(sp)
        actuals.append(state["vx"])
        controls.append(control)

        t += dt

    return {
        "times": np.array(times),
        "setpoints": np.array(setpoints),
        "actuals": np.array(actuals),
        "controls": np.array(controls),
    }


def main():
    config_dir = Path(__file__).parent.parent / "configs"
    robot = load_robot(config_dir / "ideal_robot.yaml")

    print("Control Loop Analysis Example")
    print("=" * 50)

    # Test different PID tunings
    tunings = [
        ("Underdamped", PIDController(kp=5.0, ki=1.0, kd=0.1)),
        ("Well-tuned", PIDController(kp=3.0, ki=0.5, kd=0.5)),
        ("Overdamped", PIDController(kp=1.0, ki=0.1, kd=1.0)),
    ]

    setpoint = 0.5  # m/s
    duration = 5.0
    dt = 0.01

    fig, axes = plt.subplots(len(tunings), 2, figsize=(14, 4 * len(tunings)))

    for i, (name, pid) in enumerate(tunings):
        print(f"\nTesting {name} controller (Kp={pid.kp}, Ki={pid.ki}, Kd={pid.kd})")

        # Run test
        data = run_step_response_test(robot, pid, setpoint, duration, dt)

        # Find step start index
        step_start = np.argmax(data["setpoints"] > 0)
        t_step = data["times"][step_start:]
        y_step = data["actuals"][step_start:]

        # Analyze step response
        metrics = analyze_step_response(
            t_step - t_step[0],
            y_step,
            setpoint=setpoint,
            initial=0.0,
        )

        print(f"  Rise time: {metrics.rise_time_s*1000:.1f} ms" if metrics.rise_time_s else "  Rise time: N/A")
        print(f"  Settling time: {metrics.settling_time_s*1000:.1f} ms" if metrics.settling_time_s else "  Settling time: N/A")
        print(f"  Overshoot: {metrics.overshoot_percent:.1f}%" if metrics.overshoot_percent else "  Overshoot: 0%")
        print(f"  RMSE: {metrics.rmse:.4f}")

        # Plot step response
        plot_step_response(
            data["times"],
            data["actuals"],
            setpoint=setpoint,
            metrics=metrics,
            ax=axes[i, 0],
            title=f"{name}: Step Response",
        )

        # Plot control effort
        axes[i, 1].plot(data["times"], data["controls"], "m-", linewidth=1.5)
        axes[i, 1].set_title(f"{name}: Control Effort")
        axes[i, 1].set_xlabel("Time (s)")
        axes[i, 1].set_ylabel("Control")
        axes[i, 1].grid(True, alpha=0.3)
        axes[i, 1].axhline(y=0, color="k", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig("02_control_loop_analysis.png", dpi=150)
    print("\nSaved plot to: 02_control_loop_analysis.png")
    plt.show()


if __name__ == "__main__":
    main()
