#!/usr/bin/env python3
"""
Example 03: System Identification

Demonstrates:
- Collecting step response data from simulation
- Identifying first-order and second-order models
- Comparing model fit quality
- Motor parameter estimation
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mara_host.research.config_loader import load_robot
from mara_host.research.simulation import DCMotor, DCMotorConfig
from mara_host.research.sysid import (
    identify_first_order_step,
    identify_second_order_step,
    fit_step_response,
    identify_dc_motor_step,
    identify_coulomb_friction,
)
from mara_host.research.plotting import create_figure


def collect_motor_step_response(motor: DCMotor, voltage: float, duration: float, dt: float):
    """Collect step response data from motor."""
    times = []
    voltages = []
    velocities = []
    currents = []

    t = 0.0
    motor.reset()

    while t < duration:
        # Apply step voltage
        v = voltage if t > 0.1 else 0.0

        state = motor.step(v, 0.0, dt)

        times.append(t)
        voltages.append(v)
        velocities.append(state["velocity"])
        currents.append(state["current"])

        t += dt

    return {
        "times": np.array(times),
        "voltages": np.array(voltages),
        "velocities": np.array(velocities),
        "currents": np.array(currents),
    }


def main():
    print("System Identification Example")
    print("=" * 50)

    # Create a motor with known parameters
    true_config = DCMotorConfig(
        R=2.0,
        L=0.001,
        Kv=0.02,
        Kt=0.02,
        J=0.005,
        b=0.001,
        Kf=0.01,
        max_voltage=12.0,
        max_current=10.0,
        max_velocity=100.0,
    )

    motor = DCMotor(true_config)
    print(f"\nTrue motor parameters:")
    print(f"  R = {true_config.R} Ohm")
    print(f"  Kv = {true_config.Kv} V/(rad/s)")
    print(f"  J = {true_config.J} kg·m²")
    print(f"  b = {true_config.b} N·m·s/rad")

    # Collect step response data
    print("\nCollecting step response data...")
    data = collect_motor_step_response(motor, voltage=6.0, duration=2.0, dt=0.001)

    # Find step start
    step_start = np.argmax(data["voltages"] > 0)
    t = data["times"][step_start:] - data["times"][step_start]
    v = data["velocities"][step_start:]

    # Identify first-order model
    params_1st = identify_first_order_step(t, v, input_amplitude=6.0)
    print(f"\nFirst-order model identification:")
    print(f"  K = {params_1st.K:.4f}")
    print(f"  tau = {params_1st.tau:.4f} s")

    # Identify second-order model
    params_2nd = identify_second_order_step(t, v, input_amplitude=6.0)
    print(f"\nSecond-order model identification:")
    print(f"  K = {params_2nd.K:.4f}")
    print(f"  wn = {params_2nd.wn:.4f} rad/s ({params_2nd.fn_hz:.2f} Hz)")
    print(f"  zeta = {params_2nd.zeta:.4f}")

    # Fit models with optimization
    fitted_1st, fit_params_1st = fit_step_response(t, v, order=1, input_amplitude=6.0)
    fitted_2nd, fit_params_2nd = fit_step_response(t, v, order=2, input_amplitude=6.0)

    print(f"\nOptimized first-order fit:")
    print(f"  K = {fit_params_1st['K']:.4f}")
    print(f"  tau = {fit_params_1st['tau']:.4f} s")

    print(f"\nOptimized second-order fit:")
    print(f"  K = {fit_params_2nd['K']:.4f}")
    print(f"  wn = {fit_params_2nd['wn']:.4f} rad/s")
    print(f"  zeta = {fit_params_2nd['zeta']:.4f}")

    # Identify DC motor parameters
    motor_params = identify_dc_motor_step(
        data["times"],
        data["voltages"],
        data["velocities"],
        data["currents"],
    )
    print(f"\nIdentified motor parameters:")
    print(f"  Km = {motor_params.Km:.4f} (true: {true_config.Kv})")
    print(f"  tau_m = {motor_params.tau_m:.4f} s")

    # Plot results
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Step response with model fits
    axes[0, 0].plot(t, v, "b-", linewidth=2, label="Measured")
    axes[0, 0].plot(t, fitted_1st, "r--", linewidth=1.5, label="1st order fit")
    axes[0, 0].plot(t, fitted_2nd, "g--", linewidth=1.5, label="2nd order fit")
    axes[0, 0].set_title("Motor Step Response")
    axes[0, 0].set_xlabel("Time (s)")
    axes[0, 0].set_ylabel("Velocity (rad/s)")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # Current response
    axes[0, 1].plot(data["times"], data["currents"], "m-", linewidth=1.5)
    axes[0, 1].set_title("Motor Current")
    axes[0, 1].set_xlabel("Time (s)")
    axes[0, 1].set_ylabel("Current (A)")
    axes[0, 1].grid(True, alpha=0.3)

    # Error comparison
    error_1st = v - fitted_1st
    error_2nd = v - fitted_2nd
    axes[1, 0].plot(t, error_1st, "r-", alpha=0.7, label="1st order error")
    axes[1, 0].plot(t, error_2nd, "g-", alpha=0.7, label="2nd order error")
    axes[1, 0].set_title("Model Fit Error")
    axes[1, 0].set_xlabel("Time (s)")
    axes[1, 0].set_ylabel("Error (rad/s)")
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # Residual histogram
    axes[1, 1].hist(error_1st, bins=30, alpha=0.5, label="1st order", color="red")
    axes[1, 1].hist(error_2nd, bins=30, alpha=0.5, label="2nd order", color="green")
    axes[1, 1].set_title("Residual Distribution")
    axes[1, 1].set_xlabel("Error")
    axes[1, 1].set_ylabel("Count")
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("03_system_identification.png", dpi=150)
    print("\nSaved plot to: 03_system_identification.png")
    plt.show()


if __name__ == "__main__":
    main()
