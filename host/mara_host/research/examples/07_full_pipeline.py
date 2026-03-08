#!/usr/bin/env python3
"""
Example 07: Full Research Pipeline

Demonstrates a complete research workflow:
1. Load robot from config
2. Design and simulate a controller
3. Record session data
4. Analyze metrics and performance
5. Identify system parameters
6. Generate comprehensive report

This example ties together all research module capabilities.
"""
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mara_host.research.config_loader import SimulationConfig
from mara_host.research.metrics import (
    analyze_step_response,
    compute_tracking_error,
)
from mara_host.research.sysid import (
    identify_first_order_step,
    identify_second_order_step,
    fit_step_response,
)
from mara_host.research.analysis import (
    compute_signal_stats,
    compute_fft,
)
from mara_host.research.plotting import (
    plot_trajectory_2d,
    plot_step_response,
)


# =============================================================================
# Controller Implementation
# =============================================================================

@dataclass
class VelocityPID:
    """Velocity tracking PID controller."""
    kp_v: float = 2.0      # Linear velocity P gain
    ki_v: float = 0.5      # Linear velocity I gain
    kd_v: float = 0.1      # Linear velocity D gain
    kp_w: float = 3.0      # Angular velocity P gain

    def __post_init__(self):
        self.integral_v = 0.0
        self.prev_error_v = 0.0
        self.vx_target = 0.0
        self.omega_target = 0.0

    def set_target(self, vx: float, omega: float):
        self.vx_target = vx
        self.omega_target = omega

    def update(self, state: dict, dt: float) -> Tuple[float, float]:
        """Compute control output."""
        # Velocity error
        error_v = self.vx_target - state["vx"]

        # PID for linear velocity
        self.integral_v += error_v * dt
        self.integral_v = np.clip(self.integral_v, -1.0, 1.0)
        derivative_v = (error_v - self.prev_error_v) / dt if dt > 0 else 0.0

        vx_out = (
            self.kp_v * error_v +
            self.ki_v * self.integral_v +
            self.kd_v * derivative_v
        )

        # P control for angular velocity
        error_w = self.omega_target - state["omega"]
        omega_out = self.kp_w * error_w

        self.prev_error_v = error_v

        return float(vx_out), float(omega_out)

    def reset(self):
        self.integral_v = 0.0
        self.prev_error_v = 0.0


# =============================================================================
# Trajectory Generator
# =============================================================================

def generate_test_trajectory(t: float) -> Tuple[float, float]:
    """Generate velocity commands for testing."""
    if t < 1.0:
        return 0.0, 0.0           # Start stationary
    elif t < 3.0:
        return 0.5, 0.0           # Forward
    elif t < 5.0:
        return 0.3, 0.5           # Turn left
    elif t < 7.0:
        return 0.4, 0.0           # Forward
    elif t < 9.0:
        return 0.3, -0.5          # Turn right
    elif t < 11.0:
        return 0.5, 0.0           # Forward
    else:
        return 0.0, 0.0           # Stop


# =============================================================================
# Main Pipeline
# =============================================================================

def main():
    print("=" * 60)
    print("FULL RESEARCH PIPELINE EXAMPLE")
    print("=" * 60)

    output_dir = Path("pipeline_output")
    output_dir.mkdir(exist_ok=True)

    # -------------------------------------------------------------------------
    # Step 1: Load Robot Configuration
    # -------------------------------------------------------------------------
    print("\n📦 Step 1: Loading robot configuration...")

    config_dir = Path(__file__).parent.parent / "configs"
    config = SimulationConfig(config_dir / "medium_robot.yaml")

    print(f"   Robot: {config.name}")
    print(f"   Description: {config.description}")
    print(f"   Wheel radius: {config.drive_config.wheel_radius}m")
    print(f"   Wheel base: {config.drive_config.wheel_base}m")
    print(f"   Max linear vel: {config.drive_config.max_linear_vel} m/s")

    robot = config.create_robot()
    controller = VelocityPID()

    # -------------------------------------------------------------------------
    # Step 2: Run Simulation with Controller
    # -------------------------------------------------------------------------
    print("\n🚀 Step 2: Running simulation...")

    duration = 15.0
    dt = 0.01
    t = 0.0

    # Data collection
    times = []
    vx_refs = []
    vx_acts = []
    omega_refs = []
    omega_acts = []
    pos_x = []
    pos_y = []
    pos_theta = []
    imu_data = []

    robot.reset()
    controller.reset()

    while t < duration:
        # Get trajectory command
        vx_ref, omega_ref = generate_test_trajectory(t)
        controller.set_target(vx_ref, omega_ref)

        # Get robot state
        state = robot.get_state()

        # Compute control
        vx_cmd, omega_cmd = controller.update(state, dt)

        # Apply (with saturation)
        vx_cmd = np.clip(vx_cmd, -config.drive_config.max_linear_vel,
                        config.drive_config.max_linear_vel)
        omega_cmd = np.clip(omega_cmd, -config.drive_config.max_angular_vel,
                           config.drive_config.max_angular_vel)

        robot.set_velocity(vx_cmd, omega_cmd)
        new_state = robot.step(dt)
        imu = robot.get_imu_reading()

        # Record data
        times.append(t)
        vx_refs.append(vx_ref)
        vx_acts.append(new_state["vx"])
        omega_refs.append(omega_ref)
        omega_acts.append(new_state["omega"])
        pos_x.append(new_state["x"])
        pos_y.append(new_state["y"])
        pos_theta.append(new_state["theta"])
        imu_data.append(imu)

        t += dt

    # Convert to arrays
    times = np.array(times)
    vx_refs = np.array(vx_refs)
    vx_acts = np.array(vx_acts)
    omega_refs = np.array(omega_refs)
    omega_acts = np.array(omega_acts)
    pos_x = np.array(pos_x)
    pos_y = np.array(pos_y)

    print(f"   Completed {len(times)} simulation steps")
    print(f"   Final position: ({pos_x[-1]:.3f}, {pos_y[-1]:.3f})")

    # -------------------------------------------------------------------------
    # Step 3: Analyze Control Performance
    # -------------------------------------------------------------------------
    print("\n📊 Step 3: Analyzing control performance...")

    rmse_vx, mae_vx, max_err_vx = compute_tracking_error(vx_refs, vx_acts)
    rmse_omega, mae_omega, max_err_omega = compute_tracking_error(omega_refs, omega_acts)

    print(f"   Linear velocity tracking:")
    print(f"      RMSE: {rmse_vx:.4f} m/s")
    print(f"      MAE: {mae_vx:.4f} m/s")
    print(f"      Max error: {max_err_vx:.4f} m/s")

    print(f"   Angular velocity tracking:")
    print(f"      RMSE: {rmse_omega:.4f} rad/s")
    print(f"      MAE: {mae_omega:.4f} rad/s")
    print(f"      Max error: {max_err_omega:.4f} rad/s")

    # Find step response segment (first acceleration)
    step_start = np.argmax(vx_refs > 0)
    step_end = min(step_start + 200, len(times))
    t_step = times[step_start:step_end] - times[step_start]
    v_step = vx_acts[step_start:step_end]

    step_metrics = analyze_step_response(t_step, v_step, setpoint=0.5)
    print(f"\n   Step response analysis:")
    if step_metrics.rise_time_s:
        print(f"      Rise time: {step_metrics.rise_time_s*1000:.1f} ms")
    if step_metrics.settling_time_s:
        print(f"      Settling time: {step_metrics.settling_time_s*1000:.1f} ms")
    if step_metrics.overshoot_percent:
        print(f"      Overshoot: {step_metrics.overshoot_percent:.1f}%")

    # -------------------------------------------------------------------------
    # Step 4: System Identification
    # -------------------------------------------------------------------------
    print("\n🔬 Step 4: System identification...")

    params_1st = identify_first_order_step(t_step, v_step, input_amplitude=0.5)
    params_2nd = identify_second_order_step(t_step, v_step, input_amplitude=0.5)

    print(f"   First-order model: K={params_1st.K:.4f}, tau={params_1st.tau*1000:.1f}ms")
    print(f"   Second-order model: K={params_2nd.K:.4f}, wn={params_2nd.wn:.2f}rad/s, zeta={params_2nd.zeta:.4f}")

    # -------------------------------------------------------------------------
    # Step 5: Signal Analysis
    # -------------------------------------------------------------------------
    print("\n📈 Step 5: Signal analysis...")

    # Analyze IMU gyro signal
    gz = np.array([imu["gz"] for imu in imu_data])
    gz_stats = compute_signal_stats(gz)

    print(f"   IMU gyro (z-axis) statistics:")
    print(f"      Mean: {gz_stats.mean:.4f} rad/s")
    print(f"      Std: {gz_stats.std:.4f} rad/s")
    print(f"      Range: [{gz_stats.min:.4f}, {gz_stats.max:.4f}]")

    # FFT of gyro signal
    freqs, mags = compute_fft(gz, sample_rate_hz=1.0/dt)
    dominant_idx = np.argmax(mags[1:]) + 1  # Skip DC
    print(f"      Dominant frequency: {freqs[dominant_idx]:.2f} Hz")

    # -------------------------------------------------------------------------
    # Step 6: Generate Report and Visualizations
    # -------------------------------------------------------------------------
    print("\n📝 Step 6: Generating report and visualizations...")

    # Create comprehensive figure
    fig = plt.figure(figsize=(16, 12))

    # Trajectory
    ax1 = fig.add_subplot(2, 3, 1)
    plot_trajectory_2d(pos_x, pos_y, ax=ax1, title=f"{config.name} Trajectory")

    # Linear velocity tracking
    ax2 = fig.add_subplot(2, 3, 2)
    ax2.plot(times, vx_refs, "b--", linewidth=2, label="Reference")
    ax2.plot(times, vx_acts, "r-", alpha=0.8, label="Actual")
    ax2.fill_between(times, vx_refs - 0.05, vx_refs + 0.05, alpha=0.2, color="blue")
    ax2.set_title("Linear Velocity Tracking")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Velocity (m/s)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Angular velocity tracking
    ax3 = fig.add_subplot(2, 3, 3)
    ax3.plot(times, omega_refs, "b--", linewidth=2, label="Reference")
    ax3.plot(times, omega_acts, "r-", alpha=0.8, label="Actual")
    ax3.set_title("Angular Velocity Tracking")
    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("Angular velocity (rad/s)")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Step response with model fit
    ax4 = fig.add_subplot(2, 3, 4)
    fitted_1st, _ = fit_step_response(t_step, v_step, order=1, input_amplitude=0.5)
    ax4.plot(t_step, v_step, "b-", linewidth=2, label="Measured")
    ax4.plot(t_step, fitted_1st, "r--", linewidth=1.5, label="1st order fit")
    ax4.axhline(y=0.5, color="g", linestyle=":", label="Setpoint")
    plot_step_response(t_step, v_step, setpoint=0.5, metrics=step_metrics, ax=ax4,
                      title="Step Response Analysis")

    # Tracking error
    ax5 = fig.add_subplot(2, 3, 5)
    error_vx = vx_refs - vx_acts
    ax5.plot(times, error_vx, "g-", alpha=0.8)
    ax5.axhline(y=0, color="k", linestyle="--", alpha=0.5)
    ax5.axhline(y=rmse_vx, color="r", linestyle="--", alpha=0.5, label=f"RMSE: {rmse_vx:.4f}")
    ax5.axhline(y=-rmse_vx, color="r", linestyle="--", alpha=0.5)
    ax5.set_title("Velocity Tracking Error")
    ax5.set_xlabel("Time (s)")
    ax5.set_ylabel("Error (m/s)")
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # Performance summary
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.axis("off")

    summary_text = f"""
    PERFORMANCE SUMMARY
    {"="*40}

    Robot: {config.name}

    Tracking Performance:
      • Linear velocity RMSE: {rmse_vx:.4f} m/s
      • Angular velocity RMSE: {rmse_omega:.4f} rad/s

    Step Response:
      • Rise time: {step_metrics.rise_time_s*1000:.1f} ms
      • Settling time: {step_metrics.settling_time_s*1000 if step_metrics.settling_time_s else 'N/A':.1f} ms
      • Overshoot: {step_metrics.overshoot_percent if step_metrics.overshoot_percent else 0:.1f}%

    System Identification:
      • 1st order: K={params_1st.K:.3f}, τ={params_1st.tau*1000:.1f}ms
      • 2nd order: K={params_2nd.K:.3f}, ωn={params_2nd.wn:.2f}, ζ={params_2nd.zeta:.3f}

    Simulation:
      • Duration: {duration} s
      • Sample rate: {1/dt:.0f} Hz
      • Total samples: {len(times)}
    """

    ax6.text(0.1, 0.9, summary_text, transform=ax6.transAxes,
             fontsize=10, fontfamily="monospace", verticalalignment="top")

    plt.tight_layout()

    # Save figure
    fig_path = output_dir / "07_full_pipeline.png"
    plt.savefig(fig_path, dpi=150)
    print(f"   Saved figure: {fig_path}")

    # Save report as JSON
    report = {
        "robot": config.name,
        "simulation": {
            "duration_s": duration,
            "dt_s": dt,
            "n_samples": len(times),
        },
        "tracking": {
            "linear_velocity": {
                "rmse": rmse_vx,
                "mae": mae_vx,
                "max_error": max_err_vx,
            },
            "angular_velocity": {
                "rmse": rmse_omega,
                "mae": mae_omega,
                "max_error": max_err_omega,
            },
        },
        "step_response": step_metrics.to_dict(),
        "system_id": {
            "first_order": params_1st.to_dict(),
            "second_order": params_2nd.to_dict(),
        },
        "final_position": {
            "x": pos_x[-1],
            "y": pos_y[-1],
        },
    }

    report_path = output_dir / "07_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"   Saved report: {report_path}")

    print("\n✅ Pipeline complete!")
    plt.show()


if __name__ == "__main__":
    main()
