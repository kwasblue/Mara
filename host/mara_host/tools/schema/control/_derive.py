# schema/control/_derive.py
"""
State-space derivation functions for control blocks.

These functions convert block parameters into state-space matrices
(A, B, C, D, K, L) for firmware upload.

All functions follow the signature:
    derive_xxx(params: dict) -> dict[str, list[float]]

Returns dict with keys: A, B, C, D, K (for controllers) or A, B, C, L (for observers)
Matrices are returned as flat lists in row-major order.
"""

import math
from typing import Optional


def derive_integrator_state_space(params: dict) -> dict[str, list[float]]:
    """
    Integrator: dx/dt = u, y = K*x

    State-space: A=0, B=1, C=gain
    """
    gain = params.get("gain", 1.0)
    return {
        "A": [0.0],
        "B": [1.0],
        "C": [gain],
        "D": [0.0],
        "K": [0.0],  # No state feedback
    }


def derive_derivative_state_space(params: dict) -> dict[str, list[float]]:
    """
    Filtered derivative: H(s) = K*N*s / (s + N)

    Equivalent state-space:
        dx/dt = -N*x + N*u
        y = K*x

    Where N is the filter coefficient (bandwidth).
    """
    gain = params.get("gain", 1.0)
    N = params.get("filter_coeff", 100.0)

    return {
        "A": [-N],
        "B": [N],
        "C": [gain],
        "D": [0.0],
        "K": [0.0],
    }


def derive_gain_state_space(params: dict) -> Optional[dict[str, list[float]]]:
    """
    Pure gain: y = K*u

    Unity gain returns None (no slot needed).
    Other gains: A=0, B=0, C=K (pass-through)
    """
    gain = params.get("gain", 1.0)

    if abs(gain - 1.0) < 1e-9:
        return None  # Unity gain, no slot needed

    return {
        "A": [0.0],
        "B": [0.0],
        "C": [gain],
        "D": [0.0],  # Actually D=K for pure feedthrough, but we use C
        "K": [0.0],
    }


def derive_filter_state_space(params: dict) -> dict[str, list[float]]:
    """
    Low-pass or high-pass filter.

    1st order LP: H(s) = wc / (s + wc)
        dx/dt = -wc*x + wc*u
        y = x

    1st order HP: H(s) = s / (s + wc)
        dx/dt = -wc*x + u
        y = -wc*x + u  (requires D term)

    Higher orders: cascade of 1st order sections (Butterworth).
    """
    cutoff_hz = params.get("cutoff_freq", 10.0)
    order = params.get("order", 1)
    filter_type = params.get("filter_type", "lowpass")

    wc = 2 * math.pi * cutoff_hz

    if order == 1:
        if filter_type == "lowpass":
            return {
                "A": [-wc],
                "B": [wc],
                "C": [1.0],
                "D": [0.0],
                "K": [0.0],
            }
        else:  # highpass
            return {
                "A": [-wc],
                "B": [1.0],
                "C": [-wc],
                "D": [1.0],
                "K": [0.0],
            }

    elif order == 2:
        # 2nd order Butterworth: poles at wc * exp(±j*3π/4)
        # Canonical form with damping ratio ζ = 1/√2
        zeta = 1.0 / math.sqrt(2)

        # State-space in controllable canonical form
        A = [
            0.0, 1.0,
            -wc * wc, -2 * zeta * wc
        ]
        B = [0.0, wc * wc]
        C = [1.0, 0.0]

        return {
            "A": A,
            "B": B,
            "C": C,
            "D": [0.0],
            "K": [0.0, 0.0],
        }

    else:
        # Higher order: approximate with cascaded 1st order
        # Each section has wc_eff = wc for matching bandwidth
        # (Simplified - full Butterworth would need proper pole placement)
        A = [-wc]
        B = [wc]
        C = [1.0]
        return {
            "A": A,
            "B": B,
            "C": C,
            "D": [0.0],
            "K": [0.0],
        }


def derive_notch_state_space(params: dict) -> dict[str, list[float]]:
    """
    Notch filter (band-reject).

    H(s) = (s² + wn²) / (s² + (wn/Q)*s + wn²)

    Where wn = 2*π*f_center, Q = f_center / bandwidth
    """
    f_center = params.get("center_freq", 50.0)
    bandwidth = params.get("bandwidth", 5.0)

    wn = 2 * math.pi * f_center
    Q = f_center / bandwidth

    # State-space in observable canonical form
    # 2 states for 2nd order system
    A = [
        0.0, 1.0,
        -wn * wn, -wn / Q
    ]
    B = [0.0, 1.0]
    C = [wn * wn, -wn / Q]  # Zeros at ±j*wn
    D = [1.0]  # Feedthrough for proper notch

    return {
        "A": A,
        "B": B,
        "C": C,
        "D": D,
        "K": [0.0, 0.0],
    }


def derive_moving_avg_state_space(params: dict) -> dict[str, list[float]]:
    """
    Moving average approximated as 1st order LP.

    MA bandwidth ≈ fs / (2*π*N) where N is window size.
    We match this with a 1st order LP.
    """
    window_size = params.get("window_size", 5)
    rate_hz = params.get("rate_hz", 100)  # Assume 100Hz if not specified

    # Equivalent cutoff frequency
    fc = rate_hz / (2 * math.pi * window_size)
    wc = 2 * math.pi * fc

    return {
        "A": [-wc],
        "B": [wc],
        "C": [1.0],
        "D": [0.0],
        "K": [0.0],
    }


def derive_delay_pade(params: dict) -> dict[str, list[float]]:
    """
    Delay approximated using 1st order Padé approximation.

    e^(-sT) ≈ (1 - sT/2) / (1 + sT/2)

    State-space:
        dx/dt = -2/T * x + 2/T * u
        y = -x + u
    """
    T = params.get("delay_time", 0.1)

    if T < 0.001:
        # Very small delay - just pass through
        return {
            "A": [0.0],
            "B": [0.0],
            "C": [0.0],
            "D": [1.0],
            "K": [0.0],
        }

    k = 2.0 / T

    return {
        "A": [-k],
        "B": [k],
        "C": [-1.0],
        "D": [1.0],
        "K": [0.0],
    }


def derive_kalman_gain(params: dict) -> dict[str, list[float]]:
    """
    Compute steady-state Kalman gain from Q and R.

    This solves the algebraic Riccati equation:
        A*P + P*A' - P*C'*inv(R)*C*P + Q = 0
        L = P*C'*inv(R)

    For simplicity, we use a heuristic for small systems.
    Full DARE solver would be used for production.
    """
    n = params.get("num_states", 2)
    A = params.get("A", [0.0] * (n * n))
    C = params.get("C", [1.0] + [0.0] * (n - 1))
    Q = params.get("Q", [1.0] * n)  # Process noise (diagonal assumed)
    R = params.get("R", [1.0])       # Measurement noise (scalar assumed)

    # Heuristic gain: L ≈ sqrt(Q/R) for diagonal Q
    # This gives reasonable pole placement for many systems
    if isinstance(Q, list) and len(Q) >= n:
        Q_diag = Q[:n]
    else:
        Q_diag = [1.0] * n

    R_val = R[0] if isinstance(R, list) else R
    if R_val == 0:
        R_val = 1.0

    L = [math.sqrt(abs(q) / R_val) for q in Q_diag]

    return {
        "A": A,
        "B": params.get("B", [0.0] * n),
        "C": C,
        "L": L,
    }


def derive_velocity_observer(params: dict) -> dict[str, list[float]]:
    """
    Velocity observer from position measurement.

    State: [pos, vel]
    Model: d/dt[pos; vel] = [0 1; 0 0][pos; vel] + [0; 0]u
    Output: y = [1 0][pos; vel] = pos

    Observer gain L places poles for desired bandwidth.
    """
    filter_hz = params.get("filter_hz", 20.0)
    wn = 2 * math.pi * filter_hz

    # Place poles at -wn (critically damped double pole)
    # For this system, L = [2*wn, wn^2]
    L = [2 * wn, wn * wn]

    return {
        "A": [0.0, 1.0, 0.0, 0.0],  # 2x2 row-major
        "B": [0.0, 0.0],
        "C": [1.0, 0.0],
        "L": L,
    }


def derive_complementary_state_space(params: dict) -> dict[str, list[float]]:
    """
    Complementary filter as state-space.

    High-pass on gyro + low-pass on accel.
    angle = alpha * (angle + gyro*dt) + (1-alpha) * accel_angle

    As continuous: d(angle)/dt = -wc*angle + wc*accel + gyro
    Where wc = (1-alpha) / (alpha * dt)
    """
    alpha = params.get("alpha", 0.98)
    dt = params.get("dt", 0.01)

    # Cutoff frequency from alpha
    if alpha >= 1.0:
        wc = 0.01  # Very low cutoff
    else:
        wc = (1 - alpha) / (alpha * dt)

    # 2-input system: [gyro, accel]
    # d(angle)/dt = -wc*angle + gyro + wc*accel
    return {
        "A": [-wc],
        "B": [1.0, wc],  # B is 1x2 for 2 inputs
        "C": [1.0],
        "L": [wc],  # Observer-like correction from accel
    }


def derive_disturbance_observer(params: dict) -> dict[str, list[float]]:
    """
    Disturbance observer.

    Augmented state: [x, d] where d is the disturbance.
    Model: d/dt[x; d] = [A 1; 0 0][x; d] + [B; 0]u

    Observer estimates d from y - plant_model(u).
    """
    bandwidth_hz = params.get("bandwidth_hz", 10.0)
    plant_gain = params.get("plant_gain", 1.0)

    wc = 2 * math.pi * bandwidth_hz

    # Simple 1st order plant + disturbance state
    # A_aug = [[-wc, 1], [0, 0]]
    # B_aug = [[wc * plant_gain], [0]]
    # C_aug = [[1, 0]]

    A = [-wc, 1.0, 0.0, 0.0]  # 2x2
    B = [wc * plant_gain, 0.0]
    C = [1.0, 0.0]
    L = [2 * wc, wc * wc]  # Critically damped observer

    return {
        "A": A,
        "B": B,
        "C": C,
        "L": L,
    }


def derive_feedforward_state_space(params: dict) -> dict[str, list[float]]:
    """
    Feedforward controller.

    FF = gain * ref + vel_gain * d(ref)/dt + accel_gain * d²(ref)/dt²

    Using filtered derivatives:
        state 1: filtered ref derivative
        state 2: filtered 2nd derivative
    """
    gain = params.get("gain", 1.0)
    vel_gain = params.get("velocity_gain", 0.0)
    accel_gain = params.get("accel_gain", 0.0)

    N = 100.0  # Derivative filter coefficient

    if accel_gain == 0.0 and vel_gain == 0.0:
        # Pure gain feedforward
        return {
            "A": [0.0],
            "B": [0.0],
            "C": [gain],
            "D": [0.0],
            "K": [0.0],
        }

    if accel_gain == 0.0:
        # 1st order: position + velocity feedforward
        return {
            "A": [-N],
            "B": [N],
            "C": [vel_gain],
            "D": [gain],  # Direct feedthrough for position term
            "K": [0.0],
        }

    # 2nd order: position + velocity + acceleration
    return {
        "A": [-N, 0.0, 1.0, -N],  # 2x2, derivative chain
        "B": [N, 0.0],
        "C": [vel_gain, accel_gain],
        "D": [gain],
        "K": [0.0, 0.0],
    }


def derive_lqr_state_space(params: dict) -> dict[str, list[float]]:
    """
    LQR as state-space: u = -K*(x - x_ref).

    The K matrix is typically designed offline (MATLAB, Python control).
    This just validates and reformats for firmware.
    """
    n = params.get("num_states", 2)
    m = params.get("num_inputs", 1)
    K = params.get("K", [0.0] * (m * n))

    # LQR is feedback only, no dynamics
    # Firmware implements: u = -K*x (with reference handled separately)
    return {
        "A": [0.0] * (n * n),  # No internal state
        "B": [0.0] * n,
        "C": [0.0] * n,
        "K": K,
    }


def derive_kalman_lqg(params: dict) -> tuple[dict, dict]:
    """
    Combined Kalman + LQR (LQG).

    Returns both controller and observer configs.
    """
    n = params.get("num_states", 2)

    controller = {
        "A": params.get("A", [0.0] * (n * n)),
        "B": params.get("B", [0.0] * n),
        "C": params.get("C", [1.0] + [0.0] * (n - 1)),
        "K": params.get("K", [0.0] * n),
    }

    observer = derive_kalman_gain(params)

    return controller, observer


def derive_ekf_linearized(params: dict) -> dict[str, list[float]]:
    """
    EKF linearized at operating point.

    For MCU, we precompute the Jacobians at the nominal operating point
    and run as a standard Luenberger observer.
    """
    # Use the linear matrices directly (user provides linearized model)
    return derive_kalman_gain(params)


def derive_mpc_gain(params: dict) -> dict[str, list[float]]:
    """
    MPC precomputed as state-feedback gain.

    For infinite horizon or long horizon MPC, the optimal gain
    converges to the LQR solution. We use that approximation.
    """
    return derive_lqr_state_space(params)


# Registry of derivation functions
DERIVE_FUNCTIONS = {
    "derive_integrator_state_space": derive_integrator_state_space,
    "derive_derivative_state_space": derive_derivative_state_space,
    "derive_gain_state_space": derive_gain_state_space,
    "derive_filter_state_space": derive_filter_state_space,
    "derive_notch_state_space": derive_notch_state_space,
    "derive_moving_avg_state_space": derive_moving_avg_state_space,
    "derive_delay_pade": derive_delay_pade,
    "derive_kalman_gain": derive_kalman_gain,
    "derive_velocity_observer": derive_velocity_observer,
    "derive_complementary_state_space": derive_complementary_state_space,
    "derive_disturbance_observer": derive_disturbance_observer,
    "derive_feedforward_state_space": derive_feedforward_state_space,
    "derive_lqr_state_space": derive_lqr_state_space,
    "derive_kalman_lqg": derive_kalman_lqg,
    "derive_ekf_linearized": derive_ekf_linearized,
    "derive_mpc_gain": derive_mpc_gain,
}


def get_derive_function(name: str):
    """Get a derivation function by name."""
    return DERIVE_FUNCTIONS.get(name)


def derive_state_space(block_config: dict, params: dict) -> Optional[dict[str, list[float]]]:
    """
    Derive state-space matrices for a block given its config and parameters.

    Args:
        block_config: Block configuration from CONTROL_BLOCKS registry
        params: Runtime parameters for the block

    Returns:
        Dict with A, B, C, K/L matrices or None if not applicable
    """
    ss_config = block_config.get("state_space")
    if not ss_config:
        return None

    derive_fn_name = ss_config.get("derive_fn")
    if not derive_fn_name:
        return None

    derive_fn = get_derive_function(derive_fn_name)
    if not derive_fn:
        return None

    return derive_fn(params)
