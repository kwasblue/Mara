"""
Example usage of the control design module.

Run with: python -m mara_host.control.examples
"""

import numpy as np


def example_mass_spring_damper():
    """
    Design a state-feedback controller for a mass-spring-damper system.

    System: M*x'' + B*x' + K*x = u
    States: [position, velocity]
    """
    from mara_host.control import (
        StateSpaceModel,
        lqr,
        observer_gains,
        pole_placement,
    )
    from mara_host.control.design import reference_gain, check_stability

    print("=" * 60)
    print("Mass-Spring-Damper Control Design Example")
    print("=" * 60)

    # Physical parameters
    M = 1.0   # mass (kg)
    B = 0.5   # damping (N·s/m)
    K = 10.0  # stiffness (N/m)

    # Continuous-time state-space model
    # State: x = [position, velocity]
    # Input: u = force
    # Output: y = position
    A = np.array([
        [0, 1],
        [-K / M, -B / M]
    ])
    B_mat = np.array([[0], [1 / M]])
    C = np.array([[1, 0]])

    model = StateSpaceModel(A, B_mat, C)

    print(f"\nSystem: {model}")
    print(f"Open-loop poles: {model.poles}")
    print(f"Controllable: {model.is_controllable()}")
    print(f"Observable: {model.is_observable()}")
    print(f"Open-loop stable: {model.is_stable}")

    # -------------------------------------------------------------------------
    # Method 1: LQR Design (optimal control)
    # -------------------------------------------------------------------------
    print("\n--- LQR Design ---")

    # Weight matrices
    # Q: penalize position error heavily, velocity less
    # R: moderate control effort penalty
    Q = np.diag([100.0, 1.0])
    R = np.array([[0.1]])

    K_lqr, S, E_lqr = lqr(A, B_mat, Q, R)

    print(f"LQR gain K = {K_lqr}")
    print(f"Closed-loop poles: {E_lqr}")

    is_stable, _ = check_stability(A, B_mat, K_lqr)
    print(f"Closed-loop stable: {is_stable}")

    # Reference gain for tracking
    Kr = reference_gain(A, B_mat, C, K_lqr)
    print(f"Reference gain Kr = {Kr}")

    # -------------------------------------------------------------------------
    # Method 2: Pole Placement Design
    # -------------------------------------------------------------------------
    print("\n--- Pole Placement Design ---")

    # Desired poles: -5 +/- 5j (damping ratio ~0.7, natural freq ~7 rad/s)
    desired_poles = np.array([-5 + 5j, -5 - 5j])
    K_pp = pole_placement(A, B_mat, desired_poles)

    print(f"Pole placement gain K = {K_pp}")

    A_cl = A - B_mat @ K_pp
    actual_poles = np.linalg.eigvals(A_cl)
    print(f"Achieved poles: {actual_poles}")

    # -------------------------------------------------------------------------
    # Observer Design
    # -------------------------------------------------------------------------
    print("\n--- Observer Design ---")

    # Observer poles should be 3-5x faster than controller
    # Using real distinct poles for simplicity
    obs_poles = np.array([-25, -30])
    L = observer_gains(A, C, obs_poles)

    print(f"Observer gain L = {L.T}")  # Transpose for display

    A_obs = A - L @ C
    obs_actual_poles = np.linalg.eigvals(A_obs)
    print(f"Observer poles: {obs_actual_poles}")

    # -------------------------------------------------------------------------
    # Discretization for MCU
    # -------------------------------------------------------------------------
    print("\n--- Discretization ---")

    dt = 0.01  # 100 Hz control rate
    model_d = model.to_discrete(dt, method="zoh")

    print(f"Discrete system (dt={dt}s):")
    print(f"  Ad = \n{model_d.A}")
    print(f"  Bd = \n{model_d.B}")
    print(f"  Discrete poles: {model_d.poles}")
    print(f"  Poles inside unit circle: {np.all(np.abs(model_d.poles) < 1)}")

    return K_lqr, Kr, L


def example_dc_motor_velocity():
    """
    Design velocity controller for a DC motor.

    Model: J*omega_dot + b*omega = Kt*i
    States: [omega] (angular velocity)
    """
    from mara_host.control import StateSpaceModel, lqr
    from mara_host.control.design import integral_gain

    print("\n" + "=" * 60)
    print("DC Motor Velocity Control Example")
    print("=" * 60)

    # Motor parameters
    J = 0.01   # Inertia (kg·m²)
    b = 0.1    # Friction (N·m·s/rad)
    Kt = 0.5   # Torque constant (N·m/A)

    # First-order velocity model
    A = np.array([[-b / J]])
    B = np.array([[Kt / J]])
    C = np.array([[1]])

    model = StateSpaceModel(A, B, C)
    print(f"\nSystem: {model}")
    print(f"Open-loop pole: {model.poles[0]:.2f}")
    print(f"Time constant: {-1/model.poles[0].real:.3f} s")

    # LQR design
    Q = np.array([[10.0]])  # Penalize velocity error
    R = np.array([[0.01]])  # Allow generous control effort

    K, _, E = lqr(A, B, Q, R)
    print(f"\nLQR gain K = {K[0, 0]:.4f}")
    print(f"Closed-loop pole: {E[0]:.2f}")
    print(f"Closed-loop time constant: {-1/E[0].real:.3f} s")

    # Add integral action for zero steady-state error
    Ki = integral_gain(n_states=1, n_outputs=1, ki_diag=5.0)
    print(f"Integral gain Ki = {Ki[0, 0]:.2f}")

    return K, Ki


async def example_upload_to_mcu():
    """
    Example showing how to upload a controller to the MCU.

    NOTE: This requires an actual connection to the robot.
    """
    from mara_host.control import (
        StateSpaceModel,
        lqr,
        observer_gains,
        configure_state_feedback,
        ControllerConfig,
        upload_controller,
    )

    print("\n" + "=" * 60)
    print("MCU Upload Example (requires robot connection)")
    print("=" * 60)

    # Design a simple controller
    A = np.array([[0, 1], [-10, -0.5]])
    B = np.array([[0], [1]])
    C = np.array([[1, 0]])

    model = StateSpaceModel(A, B, C)

    # LQR design
    Q = np.diag([100, 1])
    R = np.array([[1]])
    K, _, _ = lqr(A, B, Q, R)

    # Observer design
    L = observer_gains(A, C, [-20, -25])

    print("\nTo upload this controller to the MCU:")
    print("""
    # Connect to robot
    from mara_host.command.client import RobotClient
    client = RobotClient(...)
    await client.connect()

    # Define signal IDs
    signals = {
        "state": [10, 11],      # x1, x2 from observer
        "ref": [12, 13],        # Reference position, velocity
        "control": [20],        # Control output u
        "measurement": [30],    # Position measurement y
        "input": [20],          # Control input to observer
    }

    # Configure and upload
    result = await configure_state_feedback(
        client, model, K,
        L=L,
        use_observer=True,
        signals=signals,
        controller_rate_hz=100,
        observer_rate_hz=200,
    )

    # Enable the controller
    from mara_host.control.upload import enable_controller, enable_observer
    await enable_observer(client, slot=0)
    await enable_controller(client, slot=0)
    """)


def example_discretization_comparison():
    """
    Compare different discretization methods.
    """
    from mara_host.control import StateSpaceModel, discretize

    print("\n" + "=" * 60)
    print("Discretization Method Comparison")
    print("=" * 60)

    # Oscillatory system
    A = np.array([[0, 1], [-100, -2]])
    B = np.array([[0], [1]])
    C = np.array([[1, 0]])

    model = StateSpaceModel(A, B, C)
    print(f"\nContinuous system poles: {model.poles}")

    for dt in [0.001, 0.01, 0.05]:
        print(f"\n--- dt = {dt} s ({1/dt:.0f} Hz) ---")

        for method in ["euler", "bilinear", "zoh"]:
            model_d = discretize(model, dt, method=method)
            poles = model_d.poles
            stable = np.all(np.abs(poles) < 1)

            print(f"  {method:8s}: |poles| = {np.abs(poles)}, stable={stable}")


if __name__ == "__main__":
    # Run examples
    example_mass_spring_damper()
    example_dc_motor_velocity()
    example_discretization_comparison()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
