# mara_host/research/sysid.py
"""
System identification tools for robotics.

Includes:
- Step response analysis
- Frequency response from data
- Motor parameter estimation (Km, Kv, friction, inertia)
- Transfer function fitting
- ARX/ARMAX model identification
- DC motor system identification
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import signal as scipy_signal
from scipy import optimize
from scipy import linalg


# =============================================================================
# Data Classes for System Parameters
# =============================================================================

@dataclass
class FirstOrderParams:
    """First-order system parameters: G(s) = K / (tau*s + 1)"""
    K: float = 1.0       # DC gain
    tau: float = 1.0     # Time constant (seconds)

    def transfer_function(self) -> Tuple[List[float], List[float]]:
        """Return (num, den) for scipy.signal."""
        return ([self.K], [self.tau, 1.0])

    def to_dict(self) -> Dict[str, float]:
        return {"K": self.K, "tau": self.tau}


@dataclass
class SecondOrderParams:
    """Second-order system: G(s) = K*wn^2 / (s^2 + 2*zeta*wn*s + wn^2)"""
    K: float = 1.0       # DC gain
    wn: float = 1.0      # Natural frequency (rad/s)
    zeta: float = 0.7    # Damping ratio

    @property
    def fn_hz(self) -> float:
        """Natural frequency in Hz."""
        return self.wn / (2 * np.pi)

    @property
    def is_underdamped(self) -> bool:
        return self.zeta < 1.0

    @property
    def is_critically_damped(self) -> bool:
        return abs(self.zeta - 1.0) < 1e-6

    @property
    def is_overdamped(self) -> bool:
        return self.zeta > 1.0

    def transfer_function(self) -> Tuple[List[float], List[float]]:
        """Return (num, den) for scipy.signal."""
        num = [self.K * self.wn ** 2]
        den = [1.0, 2 * self.zeta * self.wn, self.wn ** 2]
        return (num, den)

    def to_dict(self) -> Dict[str, float]:
        return {
            "K": self.K,
            "wn": self.wn,
            "zeta": self.zeta,
            "fn_hz": self.fn_hz,
        }


@dataclass
class DCMotorParams:
    """DC motor parameters for system identification."""
    Km: float = 0.0      # Motor constant (N·m/A or V/(rad/s))
    R: float = 0.0       # Armature resistance (Ohms)
    L: float = 0.0       # Armature inductance (H), often negligible
    J: float = 0.0       # Rotor inertia (kg·m²)
    b: float = 0.0       # Viscous friction (N·m·s/rad)
    Kf: float = 0.0      # Coulomb friction (N·m)

    # Derived parameters
    tau_m: float = 0.0   # Mechanical time constant (J/b)
    tau_e: float = 0.0   # Electrical time constant (L/R)

    def compute_derived(self):
        """Compute derived parameters."""
        if self.b > 0:
            self.tau_m = self.J / self.b
        if self.R > 0:
            self.tau_e = self.L / self.R

    def to_dict(self) -> Dict[str, float]:
        return {
            "Km": self.Km,
            "R": self.R,
            "L": self.L,
            "J": self.J,
            "b": self.b,
            "Kf": self.Kf,
            "tau_m": self.tau_m,
            "tau_e": self.tau_e,
        }


@dataclass
class DifferentialDriveParams:
    """Parameters for differential drive robot."""
    wheel_radius: float = 0.05      # Wheel radius (m)
    wheel_base: float = 0.2         # Distance between wheels (m)
    motor_params: DCMotorParams = field(default_factory=DCMotorParams)
    gear_ratio: float = 1.0         # Motor to wheel gear ratio
    encoder_cpr: int = 1000         # Encoder counts per revolution

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wheel_radius": self.wheel_radius,
            "wheel_base": self.wheel_base,
            "gear_ratio": self.gear_ratio,
            "encoder_cpr": self.encoder_cpr,
            "motor": self.motor_params.to_dict(),
        }


# =============================================================================
# Step Response Analysis
# =============================================================================

def identify_first_order_step(
    times: np.ndarray,
    response: np.ndarray,
    input_amplitude: float = 1.0,
    initial_value: float = 0.0,
) -> FirstOrderParams:
    """
    Identify first-order system parameters from step response.

    Uses the 63.2% method: time constant tau is when response reaches
    63.2% of final value.

    Args:
        times: Time array (seconds)
        response: Response values
        input_amplitude: Step input magnitude
        initial_value: Initial response value

    Returns:
        FirstOrderParams with K and tau
    """
    if len(times) < 3:
        return FirstOrderParams()

    # Normalize response
    y = np.array(response) - initial_value
    final_value = np.mean(y[-max(1, len(y) // 10):])

    # DC gain
    K = final_value / input_amplitude

    # Find time constant (63.2% point)
    target = 0.632 * final_value
    idx = np.argmin(np.abs(y - target))
    tau = float(times[idx] - times[0])

    return FirstOrderParams(K=K, tau=max(tau, 1e-6))


def identify_second_order_step(
    times: np.ndarray,
    response: np.ndarray,
    input_amplitude: float = 1.0,
    initial_value: float = 0.0,
) -> SecondOrderParams:
    """
    Identify second-order system parameters from step response.

    Uses overshoot and settling time to estimate wn and zeta.
    """
    if len(times) < 3:
        return SecondOrderParams()

    t = np.array(times) - times[0]
    y = np.array(response) - initial_value
    final_value = np.mean(y[-max(1, len(y) // 10):])

    # DC gain
    K = final_value / input_amplitude if abs(input_amplitude) > 1e-9 else 1.0

    # Normalize
    if abs(final_value) > 1e-9:
        y_norm = y / final_value
    else:
        return SecondOrderParams(K=K)

    # Find overshoot
    peak_idx = np.argmax(y_norm)
    peak_value = y_norm[peak_idx]
    overshoot = max(0, peak_value - 1.0)

    # Estimate damping ratio from overshoot
    if overshoot > 0:
        # Mp = exp(-pi*zeta/sqrt(1-zeta^2))
        # Solving for zeta: zeta = -ln(Mp) / sqrt(pi^2 + ln(Mp)^2)
        ln_mp = np.log(overshoot)
        zeta = -ln_mp / np.sqrt(np.pi ** 2 + ln_mp ** 2)
        zeta = np.clip(zeta, 0.01, 0.99)
    else:
        zeta = 1.0  # Critically or overdamped

    # Find peak time to estimate wn
    tp = t[peak_idx]
    if tp > 0 and zeta < 1.0:
        # tp = pi / (wn * sqrt(1 - zeta^2))
        wn = np.pi / (tp * np.sqrt(1 - zeta ** 2))
    else:
        # Use rise time estimation
        idx_10 = np.argmin(np.abs(y_norm - 0.1))
        idx_90 = np.argmin(np.abs(y_norm - 0.9))
        tr = t[idx_90] - t[idx_10]
        if tr > 0:
            # Approximate: tr ≈ 1.8/wn for zeta ≈ 0.7
            wn = 1.8 / tr
        else:
            wn = 1.0

    return SecondOrderParams(K=K, wn=wn, zeta=zeta)


def fit_step_response(
    times: np.ndarray,
    response: np.ndarray,
    order: int = 1,
    input_amplitude: float = 1.0,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Fit a transfer function model to step response data.

    Uses least-squares optimization.

    Args:
        times: Time array
        response: Response array
        order: 1 or 2 (first or second order)
        input_amplitude: Step input magnitude

    Returns:
        (fitted_response, parameters_dict)
    """
    t = np.array(times) - times[0]
    y = np.array(response)
    y0 = y[0]
    y_target = y - y0

    if order == 1:
        # First order: y(t) = K*u*(1 - exp(-t/tau))
        def model(params):
            K, tau = params
            tau = max(tau, 1e-6)
            return K * input_amplitude * (1 - np.exp(-t / tau))

        def cost(params):
            return np.sum((model(params) - y_target) ** 2)

        # Initial guess
        K0 = y_target[-1] / input_amplitude if abs(input_amplitude) > 1e-9 else 1.0
        tau0 = t[-1] / 5

        result = optimize.minimize(cost, [K0, tau0], method="Nelder-Mead")
        K, tau = result.x

        fitted = model([K, tau]) + y0
        params = {"K": K, "tau": tau, "order": 1}

    else:  # order == 2
        # Second order: complex response
        def model(params):
            K, wn, zeta = params
            wn = max(wn, 0.01)
            zeta = np.clip(zeta, 0.01, 2.0)

            sys = scipy_signal.TransferFunction(
                [K * wn ** 2],
                [1, 2 * zeta * wn, wn ** 2]
            )
            _, y_step, _ = scipy_signal.lsim(sys, np.ones_like(t) * input_amplitude, t)
            return y_step

        def cost(params):
            try:
                return np.sum((model(params) - y_target) ** 2)
            except Exception:
                return 1e10

        # Initial guess from heuristics
        params0 = identify_second_order_step(times, response, input_amplitude, y0)
        x0 = [params0.K, params0.wn, params0.zeta]

        result = optimize.minimize(cost, x0, method="Nelder-Mead")
        K, wn, zeta = result.x

        fitted = model([K, wn, zeta]) + y0
        params = {"K": K, "wn": wn, "zeta": zeta, "fn_hz": wn / (2 * np.pi), "order": 2}

    return fitted, params


# =============================================================================
# Frequency Response from Data
# =============================================================================

def estimate_frequency_response(
    input_signal: np.ndarray,
    output_signal: np.ndarray,
    sample_rate_hz: float,
    nperseg: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Estimate frequency response from input/output data.

    Uses cross-spectral density method.

    Args:
        input_signal: Input signal
        output_signal: Output signal
        sample_rate_hz: Sample rate
        nperseg: Segment length for Welch method

    Returns:
        (frequencies, magnitude_db, phase_deg)
    """
    if nperseg is None:
        nperseg = min(256, len(input_signal) // 4)

    # Cross-spectral density
    freqs, Pxy = scipy_signal.csd(input_signal, output_signal, sample_rate_hz, nperseg=nperseg)

    # Input power spectral density
    _, Pxx = scipy_signal.welch(input_signal, sample_rate_hz, nperseg=nperseg)

    # Transfer function estimate: H = Pxy / Pxx
    H = Pxy / (Pxx + 1e-10)

    magnitude_db = 20 * np.log10(np.abs(H) + 1e-10)
    phase_deg = np.angle(H, deg=True)

    # Unwrap phase
    phase_deg = np.unwrap(phase_deg * np.pi / 180) * 180 / np.pi

    return freqs, magnitude_db, phase_deg


def fit_transfer_function(
    freqs: np.ndarray,
    magnitude_db: np.ndarray,
    phase_deg: np.ndarray,
    order: int = 2,
) -> Dict[str, Any]:
    """
    Fit a transfer function model to frequency response data.

    Args:
        freqs: Frequency array (Hz)
        magnitude_db: Magnitude in dB
        phase_deg: Phase in degrees
        order: Model order (1 or 2)

    Returns:
        Dictionary with fitted parameters and model response
    """
    # Convert to rad/s
    w = 2 * np.pi * freqs

    # Convert to complex
    H_meas = 10 ** (magnitude_db / 20) * np.exp(1j * phase_deg * np.pi / 180)

    if order == 1:
        # H(jw) = K / (tau*jw + 1)
        def model(params):
            K, tau = params
            return K / (tau * 1j * w + 1)

        def cost(params):
            H_model = model(params)
            return np.sum(np.abs(H_model - H_meas) ** 2)

        # Initial guess from DC gain and -3dB point
        K0 = np.abs(H_meas[0])
        idx_3db = np.argmin(np.abs(magnitude_db - magnitude_db[0] + 3))
        tau0 = 1 / (2 * np.pi * freqs[idx_3db]) if idx_3db > 0 else 1.0

        result = optimize.minimize(cost, [K0, tau0], method="Nelder-Mead")
        K, tau = result.x

        H_fit = model([K, tau])
        params = FirstOrderParams(K=K, tau=tau)

    else:  # order == 2
        # H(jw) = K*wn^2 / (-w^2 + 2*zeta*wn*jw + wn^2)
        def model(params):
            K, wn, zeta = params
            return K * wn ** 2 / (-w ** 2 + 2 * zeta * wn * 1j * w + wn ** 2)

        def cost(params):
            try:
                H_model = model(params)
                return np.sum(np.abs(H_model - H_meas) ** 2)
            except Exception:
                return 1e10

        # Initial guess
        K0 = np.abs(H_meas[0])
        peak_idx = np.argmax(magnitude_db)
        wn0 = 2 * np.pi * freqs[peak_idx] if peak_idx > 0 else 1.0
        zeta0 = 0.5

        result = optimize.minimize(cost, [K0, wn0, zeta0], method="Nelder-Mead")
        K, wn, zeta = result.x

        H_fit = model([K, wn, zeta])
        params = SecondOrderParams(K=K, wn=wn, zeta=np.clip(zeta, 0.01, 2.0))

    return {
        "params": params,
        "freqs": freqs,
        "magnitude_db_fit": 20 * np.log10(np.abs(H_fit) + 1e-10),
        "phase_deg_fit": np.angle(H_fit, deg=True),
    }


# =============================================================================
# DC Motor System Identification
# =============================================================================

def identify_dc_motor_step(
    times: np.ndarray,
    voltage: np.ndarray,
    velocity: np.ndarray,
    current: Optional[np.ndarray] = None,
) -> DCMotorParams:
    """
    Identify DC motor parameters from step response.

    Args:
        times: Time array (seconds)
        voltage: Applied voltage (V)
        velocity: Motor velocity (rad/s)
        current: Optional current measurement (A)

    Returns:
        DCMotorParams with estimated parameters
    """
    params = DCMotorParams()

    t = np.array(times) - times[0]
    v = np.array(voltage)
    w = np.array(velocity)

    # Find steady state
    v_ss = np.mean(v[-max(1, len(v) // 10):])
    w_ss = np.mean(w[-max(1, len(w) // 10):])

    # Estimate back-EMF constant Kv (V/(rad/s))
    if abs(w_ss) > 1e-6:
        # At steady state: V = Kv*w + I*R, if no load: V ≈ Kv*w
        params.Km = v_ss / w_ss

    # Estimate mechanical time constant from velocity response
    # First-order: w(t) = w_ss * (1 - exp(-t/tau_m))
    target = 0.632 * w_ss
    idx = np.argmin(np.abs(w - target))
    params.tau_m = float(t[idx]) if t[idx] > 0 else 0.1

    # If current is available, estimate R and inertia
    if current is not None:
        i = np.array(current)
        i_ss = np.mean(i[-max(1, len(i) // 10):])

        if abs(i_ss) > 1e-6:
            # V = Kv*w + I*R -> R = (V - Kv*w) / I
            params.R = (v_ss - params.Km * w_ss) / i_ss

            # Torque constant Km = Kv (for ideal motor)
            # tau_m = J / b, and b ≈ Km * I_ss / w_ss
            if abs(w_ss) > 1e-6:
                params.b = params.Km * i_ss / w_ss
                params.J = params.tau_m * params.b

    return params


def identify_velocity_pid_plant(
    times: np.ndarray,
    setpoint: np.ndarray,
    velocity: np.ndarray,
    pwm: np.ndarray,
) -> Dict[str, Any]:
    """
    Identify plant model from closed-loop PID velocity control data.

    Uses relay feedback identification or step response fitting.

    Args:
        times: Time array
        setpoint: Velocity setpoint
        velocity: Actual velocity
        pwm: PWM/voltage output

    Returns:
        Dictionary with plant parameters and fit quality
    """
    # Simple approach: fit a first-order model to the closed-loop response
    # For more accuracy, would need open-loop data or relay identification

    # Find step changes in setpoint
    sp = np.array(setpoint)
    sp_diff = np.diff(sp)
    step_indices = np.where(np.abs(sp_diff) > np.std(sp_diff) * 2)[0]

    if len(step_indices) == 0:
        return {"error": "No clear step changes found in setpoint"}

    # Use first step response
    start_idx = step_indices[0]
    end_idx = step_indices[1] if len(step_indices) > 1 else len(times)

    t_step = np.array(times[start_idx:end_idx])
    v_step = np.array(velocity[start_idx:end_idx])
    sp_val = sp[end_idx - 1] if end_idx < len(sp) else sp[-1]

    # Fit first-order model
    params = identify_first_order_step(t_step, v_step, input_amplitude=sp_val)

    # Also fit second order for comparison
    params_2nd = identify_second_order_step(t_step, v_step, input_amplitude=sp_val)

    # Compute fit quality (R²)
    t_norm = t_step - t_step[0]
    y_pred_1st = params.K * sp_val * (1 - np.exp(-t_norm / params.tau))
    y_pred_2nd = scipy_signal.lsim(
        scipy_signal.TransferFunction(*params_2nd.transfer_function()),
        np.ones_like(t_norm) * sp_val,
        t_norm
    )[1]

    ss_res_1st = np.sum((v_step - v_step[0] - y_pred_1st) ** 2)
    ss_res_2nd = np.sum((v_step - v_step[0] - y_pred_2nd) ** 2)
    ss_tot = np.sum((v_step - np.mean(v_step)) ** 2)

    r2_1st = 1 - ss_res_1st / ss_tot if ss_tot > 0 else 0
    r2_2nd = 1 - ss_res_2nd / ss_tot if ss_tot > 0 else 0

    return {
        "first_order": params.to_dict(),
        "second_order": params_2nd.to_dict(),
        "r2_first_order": r2_1st,
        "r2_second_order": r2_2nd,
        "recommended_order": 1 if r2_1st > r2_2nd else 2,
    }


# =============================================================================
# ARX Model Identification
# =============================================================================

def identify_arx(
    u: np.ndarray,
    y: np.ndarray,
    na: int = 2,
    nb: int = 2,
    nk: int = 1,
) -> Dict[str, Any]:
    """
    Identify ARX model parameters using least squares.

    Model: y(t) = -a1*y(t-1) - ... - ana*y(t-na) + b1*u(t-nk) + ... + bnb*u(t-nk-nb+1)

    Args:
        u: Input signal
        y: Output signal
        na: Number of 'a' coefficients (autoregressive)
        nb: Number of 'b' coefficients (exogenous input)
        nk: Input delay (samples)

    Returns:
        Dictionary with 'a' and 'b' coefficient arrays
    """
    N = len(y)
    n_start = max(na, nb + nk - 1)

    if N <= n_start:
        return {"error": "Insufficient data for model order"}

    # Build regressor matrix
    n_samples = N - n_start
    n_params = na + nb

    Phi = np.zeros((n_samples, n_params))

    for i in range(n_samples):
        t = i + n_start
        # Autoregressive part
        for j in range(na):
            Phi[i, j] = -y[t - j - 1]
        # Exogenous input part
        for j in range(nb):
            Phi[i, na + j] = u[t - nk - j]

    Y = y[n_start:]

    # Least squares solution
    theta, residuals, rank, s = linalg.lstsq(Phi, Y)

    # Warn if system is underdetermined (rank < n_params means degenerate data)
    if rank < n_params:
        import warnings
        warnings.warn(
            f"ARX identification: rank {rank} < n_params {n_params}. "
            "System is underdetermined (correlated regressors or insufficient data). "
            "Estimated parameters may be unreliable.",
            stacklevel=2
        )

    a = theta[:na]
    b = theta[na:]

    # Compute prediction
    y_pred = Phi @ theta

    # R² score
    ss_res = np.sum((Y - y_pred) ** 2)
    ss_tot = np.sum((Y - np.mean(Y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    return {
        "a": a.tolist(),
        "b": b.tolist(),
        "na": na,
        "nb": nb,
        "nk": nk,
        "r2": r2,
        "y_pred": y_pred,
    }


# =============================================================================
# Friction Identification
# =============================================================================

def identify_coulomb_friction(
    velocity: np.ndarray,
    torque_or_current: np.ndarray,
) -> Tuple[float, float]:
    """
    Identify Coulomb and viscous friction from velocity-torque data.

    Model: tau = Kf*sign(v) + b*v

    Args:
        velocity: Velocity array
        torque_or_current: Torque or current array

    Returns:
        (Kf, b) - Coulomb friction coefficient and viscous friction
    """
    v = np.array(velocity)
    tau = np.array(torque_or_current)

    # Build regressor: [sign(v), v]
    Phi = np.column_stack([np.sign(v), v])

    # Least squares
    theta, _, _, _ = linalg.lstsq(Phi, tau)

    Kf = abs(theta[0])
    b = theta[1]

    return (Kf, b)


def identify_stribeck_friction(
    velocity: np.ndarray,
    torque: np.ndarray,
) -> Dict[str, float]:
    """
    Identify Stribeck friction model parameters.

    Model: tau = (Fc + (Fs - Fc)*exp(-(v/vs)^2))*sign(v) + b*v

    Args:
        velocity: Velocity array
        torque: Torque array

    Returns:
        Dictionary with Fc, Fs, vs, b parameters
    """
    v = np.array(velocity)
    tau = np.array(torque)

    def model(params, v):
        Fc, Fs, vs, b = params
        vs = max(abs(vs), 1e-6)
        return (Fc + (Fs - Fc) * np.exp(-(v / vs) ** 2)) * np.sign(v) + b * v

    def cost(params):
        return np.sum((model(params, v) - tau) ** 2)

    # Initial guess with guards against empty arrays
    v_abs = np.abs(v)
    tau_abs = np.abs(tau)

    # Guard against empty masks (e.g., constant velocity or all values equal)
    high_vel_mask = v_abs > np.percentile(v_abs, 80)
    low_vel_mask = v_abs < np.percentile(v_abs, 20)

    if np.any(high_vel_mask):
        Fc0 = float(np.median(tau_abs[high_vel_mask]))
    else:
        Fc0 = float(np.median(tau_abs)) if len(tau_abs) > 0 else 0.1

    if np.any(low_vel_mask):
        Fs0 = float(np.max(tau_abs[low_vel_mask]))
    else:
        Fs0 = float(np.max(tau_abs)) if len(tau_abs) > 0 else Fc0 * 1.5

    vs0 = float(np.percentile(v_abs, 10)) if len(v_abs) > 0 else 0.1
    vs0 = max(vs0, 1e-6)  # Ensure non-zero
    b0 = 0.01

    result = optimize.minimize(
        cost,
        [Fc0, Fs0, vs0, b0],
        method="Nelder-Mead",
        options={"maxiter": 1000},
    )

    Fc, Fs, vs, b = result.x

    return {
        "Fc": abs(Fc),
        "Fs": abs(Fs),
        "vs": abs(vs),
        "b": b,
    }
