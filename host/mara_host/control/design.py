"""
Control system design tools using scipy.

Provides LQR, pole placement, and observer gain design functions
compatible with the MCU control kernel.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union

import numpy as np
from numpy.typing import ArrayLike

from .state_space import StateSpaceModel


def lqr(
    A: ArrayLike,
    B: ArrayLike,
    Q: ArrayLike,
    R: ArrayLike,
    N: Optional[ArrayLike] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute the continuous-time LQR gain matrix K.

    Minimizes J = integral(x'Qx + u'Ru + 2x'Nu) dt

    Args:
        A: State matrix (n x n)
        B: Input matrix (n x m)
        Q: State cost matrix (n x n), must be positive semi-definite
        R: Input cost matrix (m x m), must be positive definite
        N: Cross-term matrix (n x m), defaults to zero

    Returns:
        K: Optimal gain matrix (m x n), use u = -K @ x
        S: Solution to the algebraic Riccati equation
        E: Closed-loop eigenvalues

    Example:
        # Design LQR for mass-spring-damper
        A = np.array([[0, 1], [-10, -0.5]])
        B = np.array([[0], [1]])
        Q = np.diag([100, 1])  # Penalize position error heavily
        R = np.array([[1]])    # Moderate control effort

        K, S, E = lqr(A, B, Q, R)
        print(f"Gain K = {K}")
        print(f"Closed-loop poles: {E}")
    """
    try:
        from scipy.linalg import solve_continuous_are
    except ImportError:
        raise ImportError("scipy required for LQR: pip install scipy")

    A = np.atleast_2d(np.asarray(A, dtype=np.float64))
    B = np.atleast_2d(np.asarray(B, dtype=np.float64))
    Q = np.atleast_2d(np.asarray(Q, dtype=np.float64))
    R = np.atleast_2d(np.asarray(R, dtype=np.float64))

    n = A.shape[0]
    m = B.shape[1]

    if N is None:
        N = np.zeros((n, m))
    else:
        N = np.atleast_2d(np.asarray(N, dtype=np.float64))

    # Solve the continuous-time algebraic Riccati equation
    # A'S + SA - (SB + N)R^-1(B'S + N') + Q = 0
    S = solve_continuous_are(A, B, Q, R, e=None, s=N)

    # Compute optimal gain: K = R^-1 (B'S + N')
    R_inv = np.linalg.inv(R)
    K = R_inv @ (B.T @ S + N.T)

    # Closed-loop eigenvalues
    A_cl = A - B @ K
    E = np.linalg.eigvals(A_cl)

    return K, S, E


def lqr_discrete(
    A: ArrayLike,
    B: ArrayLike,
    Q: ArrayLike,
    R: ArrayLike,
    N: Optional[ArrayLike] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute the discrete-time LQR gain matrix K.

    Minimizes J = sum(x'Qx + u'Ru + 2x'Nu)

    Args:
        A: Discrete-time state matrix (n x n)
        B: Discrete-time input matrix (n x m)
        Q: State cost matrix (n x n), must be positive semi-definite
        R: Input cost matrix (m x m), must be positive definite
        N: Cross-term matrix (n x m), defaults to zero

    Returns:
        K: Optimal gain matrix (m x n), use u = -K @ x
        S: Solution to the discrete algebraic Riccati equation
        E: Closed-loop eigenvalues

    Example:
        # Discretize system first
        sys_d = sys.to_discrete(dt=0.01)
        K, S, E = lqr_discrete(sys_d.A, sys_d.B, Q, R)
    """
    try:
        from scipy.linalg import solve_discrete_are
    except ImportError:
        raise ImportError("scipy required for LQR: pip install scipy")

    A = np.atleast_2d(np.asarray(A, dtype=np.float64))
    B = np.atleast_2d(np.asarray(B, dtype=np.float64))
    Q = np.atleast_2d(np.asarray(Q, dtype=np.float64))
    R = np.atleast_2d(np.asarray(R, dtype=np.float64))

    n = A.shape[0]
    m = B.shape[1]

    if N is None:
        N = np.zeros((n, m))
    else:
        N = np.atleast_2d(np.asarray(N, dtype=np.float64))

    # Solve discrete-time algebraic Riccati equation
    S = solve_discrete_are(A, B, Q, R, e=None, s=N)

    # Compute optimal gain: K = (R + B'SB)^-1 (B'SA + N')
    K = np.linalg.inv(R + B.T @ S @ B) @ (B.T @ S @ A + N.T)

    # Closed-loop eigenvalues
    A_cl = A - B @ K
    E = np.linalg.eigvals(A_cl)

    return K, S, E


def pole_placement(
    A: ArrayLike,
    B: ArrayLike,
    poles: ArrayLike,
) -> np.ndarray:
    """
    Compute state feedback gain K to place closed-loop poles.

    Places the eigenvalues of (A - B*K) at the specified locations.

    Args:
        A: State matrix (n x n)
        B: Input matrix (n x m)
        poles: Desired closed-loop pole locations (n complex values)

    Returns:
        K: Gain matrix (m x n), use u = -K @ x

    Example:
        # Place poles at -5 +/- 5j for fast oscillatory response
        poles = [-5 + 5j, -5 - 5j]
        K = pole_placement(A, B, poles)
    """
    try:
        from scipy.signal import place_poles
    except ImportError:
        raise ImportError("scipy required for pole placement: pip install scipy")

    A = np.atleast_2d(np.asarray(A, dtype=np.float64))
    B = np.atleast_2d(np.asarray(B, dtype=np.float64))
    poles = np.asarray(poles, dtype=np.complex128)

    result = place_poles(A, B, poles)
    return result.gain_matrix


def acker(
    A: ArrayLike,
    B: ArrayLike,
    poles: ArrayLike,
) -> np.ndarray:
    """
    Ackermann's formula for SISO pole placement.

    Only works for single-input systems. For MIMO, use pole_placement().

    Args:
        A: State matrix (n x n)
        B: Input matrix (n x 1)
        poles: Desired closed-loop pole locations (n values)

    Returns:
        K: Gain row vector (1 x n), use u = -K @ x
    """
    A = np.atleast_2d(np.asarray(A, dtype=np.float64))
    B = np.atleast_2d(np.asarray(B, dtype=np.float64))
    poles = np.asarray(poles, dtype=np.complex128)

    n = A.shape[0]
    if B.shape[1] != 1:
        raise ValueError("Ackermann's formula requires single-input (B must be n x 1)")

    # Build controllability matrix
    C_mat = B.copy()
    Ak_B = B.copy()
    for _ in range(1, n):
        Ak_B = A @ Ak_B
        C_mat = np.hstack([C_mat, Ak_B])

    # Check controllability
    if np.linalg.matrix_rank(C_mat) < n:
        raise ValueError("System is not controllable, cannot place poles")

    # Compute characteristic polynomial coefficients
    # p(s) = (s - p1)(s - p2)...(s - pn)
    poly_coeffs = np.poly(poles)  # [1, a1, a2, ..., an]

    # Compute p(A) = A^n + a1*A^(n-1) + ... + an*I
    p_A = poly_coeffs[0] * np.linalg.matrix_power(A, n)
    for i in range(1, n + 1):
        p_A = p_A + poly_coeffs[i] * np.linalg.matrix_power(A, n - i)

    # K = [0 0 ... 0 1] * C^-1 * p(A)
    e_n = np.zeros((1, n))
    e_n[0, -1] = 1.0

    K = e_n @ np.linalg.inv(C_mat) @ p_A

    return np.real(K)


def observer_gains(
    A: ArrayLike,
    C: ArrayLike,
    poles: ArrayLike,
) -> np.ndarray:
    """
    Compute observer (Luenberger) gain matrix L by pole placement.

    Places the eigenvalues of (A - L*C) at the specified locations.
    The observer is: dx_hat/dt = A*x_hat + B*u + L*(y - C*x_hat)

    Args:
        A: State matrix (n x n)
        C: Output matrix (p x n)
        poles: Desired observer pole locations (n values)

    Returns:
        L: Observer gain matrix (n x p)

    Example:
        # Observer poles should be 3-5x faster than controller poles
        controller_poles = [-5, -5]
        observer_poles = [-20, -25]  # 4-5x faster
        L = observer_gains(A, C, observer_poles)

    Note:
        The observer dynamics are dual to the controller problem.
        We solve for L by placing poles of (A' - C'*L').
    """
    A = np.atleast_2d(np.asarray(A, dtype=np.float64))
    C = np.atleast_2d(np.asarray(C, dtype=np.float64))
    poles = np.asarray(poles, dtype=np.complex128)

    # Dual problem: place poles of A' using "input" matrix C'
    # Then L = K'
    K_dual = pole_placement(A.T, C.T, poles)
    L = K_dual.T

    return L


def lqe(
    A: ArrayLike,
    C: ArrayLike,
    Q: ArrayLike,
    R: ArrayLike,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Linear Quadratic Estimator (Kalman filter) gain design.

    Computes the optimal observer gain L for the system with
    process noise covariance Q and measurement noise covariance R.

    Args:
        A: State matrix (n x n)
        C: Output matrix (p x n)
        Q: Process noise covariance (n x n), must be positive semi-definite
        R: Measurement noise covariance (p x p), must be positive definite

    Returns:
        L: Optimal observer gain matrix (n x p)
        P: Solution to the algebraic Riccati equation (estimation error covariance)
        E: Observer eigenvalues (poles of A - L*C)

    Example:
        # Design Kalman filter for noisy position measurement
        Q = np.diag([0.01, 0.1])  # Low process noise on position, more on velocity
        R = np.array([[0.1]])     # Measurement noise variance
        L, P, E = lqe(A, C, Q, R)
    """
    try:
        from scipy.linalg import solve_continuous_are
    except ImportError:
        raise ImportError("scipy required for LQE: pip install scipy")

    A = np.atleast_2d(np.asarray(A, dtype=np.float64))
    C = np.atleast_2d(np.asarray(C, dtype=np.float64))
    Q = np.atleast_2d(np.asarray(Q, dtype=np.float64))
    R = np.atleast_2d(np.asarray(R, dtype=np.float64))

    # Solve dual Riccati equation: A*P + P*A' - P*C'*R^-1*C*P + Q = 0
    P = solve_continuous_are(A.T, C.T, Q, R)

    # Optimal gain: L = P*C'*R^-1
    L = P @ C.T @ np.linalg.inv(R)

    # Observer poles
    E = np.linalg.eigvals(A - L @ C)

    return L, P, E


def check_stability(
    A: ArrayLike,
    B: ArrayLike,
    K: ArrayLike,
    continuous: bool = True,
) -> Tuple[bool, np.ndarray]:
    """
    Check if the closed-loop system A - B*K is stable.

    Args:
        A: State matrix
        B: Input matrix
        K: Feedback gain matrix
        continuous: True for continuous-time (poles in LHP),
                   False for discrete-time (poles inside unit circle)

    Returns:
        Tuple of (is_stable, poles)
    """
    A = np.atleast_2d(np.asarray(A, dtype=np.float64))
    B = np.atleast_2d(np.asarray(B, dtype=np.float64))
    K = np.atleast_2d(np.asarray(K, dtype=np.float64))

    A_cl = A - B @ K
    poles = np.linalg.eigvals(A_cl)

    if continuous:
        is_stable = bool(np.all(np.real(poles) < 0))
    else:
        is_stable = bool(np.all(np.abs(poles) < 1))

    return is_stable, poles


def reference_gain(
    A: ArrayLike,
    B: ArrayLike,
    C: ArrayLike,
    K: ArrayLike,
) -> np.ndarray:
    """
    Compute reference gain Kr for zero steady-state error.

    For tracking a constant reference r, use u = -K*x + Kr*r.
    Kr is computed to achieve y_ss = r in steady state.

    Args:
        A: State matrix (n x n)
        B: Input matrix (n x m)
        C: Output matrix (p x n)
        K: State feedback gain (m x n)

    Returns:
        Kr: Reference gain matrix (m x p)

    Note:
        Assumes the system reaches a steady state (A - B*K is stable)
        and the DC gain matrix is invertible.
    """
    A = np.atleast_2d(np.asarray(A, dtype=np.float64))
    B = np.atleast_2d(np.asarray(B, dtype=np.float64))
    C = np.atleast_2d(np.asarray(C, dtype=np.float64))
    K = np.atleast_2d(np.asarray(K, dtype=np.float64))

    A_cl = A - B @ K

    # DC gain: y_ss/r = -C * (A-BK)^-1 * B * Kr
    # For y_ss = r: Kr = -(C * (A-BK)^-1 * B)^-1
    try:
        dc_gain = C @ np.linalg.solve(A_cl, B)
        Kr = -np.linalg.inv(dc_gain)
    except np.linalg.LinAlgError:
        raise ValueError("Cannot compute reference gain: DC gain matrix is singular")

    return Kr


def integral_gain(
    n_states: int,
    n_outputs: int,
    ki_diag: Union[float, ArrayLike],
) -> np.ndarray:
    """
    Create an integral gain matrix Ki for integral action.

    The MCU state-space controller supports integral action:
    u = -K*x + Kr*r - Ki*integral(e)
    where e = r - y is the tracking error.

    Args:
        n_states: Number of states in the system
        n_outputs: Number of outputs to track
        ki_diag: Integral gain(s), scalar or array of length n_outputs

    Returns:
        Ki: Integral gain matrix (m x n_outputs)

    Example:
        # For a 2-state, 1-output system with integral gain 0.5
        Ki = integral_gain(2, 1, 0.5)
    """
    ki_diag = np.atleast_1d(np.asarray(ki_diag, dtype=np.float64))

    if ki_diag.size == 1:
        ki_diag = np.full(n_outputs, ki_diag[0])

    if ki_diag.size != n_outputs:
        raise ValueError(f"ki_diag must have {n_outputs} elements, got {ki_diag.size}")

    # Ki is typically (num_inputs x num_outputs) but for simplicity
    # we assume num_inputs == num_outputs for integral action
    Ki = np.diag(ki_diag)

    return Ki
