"""
State-space model representation and utilities.

Provides a StateSpaceModel class that wraps numpy arrays for A, B, C, D matrices
with validation, stability analysis, and discretization support.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from numpy.typing import ArrayLike


@dataclass
class StateSpaceModel:
    """
    Continuous-time state-space model: dx/dt = Ax + Bu, y = Cx + Du

    Attributes:
        A: State matrix (n x n)
        B: Input matrix (n x m)
        C: Output matrix (p x n)
        D: Feedthrough matrix (p x m), defaults to zero

    Example:
        # Mass-spring-damper: M*x'' + B*x' + K*x = u
        M, B_damp, K = 1.0, 0.5, 10.0
        A = np.array([[0, 1], [-K/M, -B_damp/M]])
        B = np.array([[0], [1/M]])
        C = np.array([[1, 0]])  # Measure position

        model = StateSpaceModel(A, B, C)
        print(model.poles)  # Check stability
    """

    A: np.ndarray
    B: np.ndarray
    C: np.ndarray
    D: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        """Convert to numpy arrays and validate dimensions."""
        self.A = np.atleast_2d(np.asarray(self.A, dtype=np.float64))
        self.B = np.atleast_2d(np.asarray(self.B, dtype=np.float64))
        self.C = np.atleast_2d(np.asarray(self.C, dtype=np.float64))

        n = self.A.shape[0]
        m = self.B.shape[1]
        p = self.C.shape[0]

        if self.D is None:
            self.D = np.zeros((p, m), dtype=np.float64)
        else:
            self.D = np.atleast_2d(np.asarray(self.D, dtype=np.float64))

        self._validate()

    def _validate(self) -> None:
        """Validate matrix dimensions are consistent."""
        n = self.num_states
        m = self.num_inputs
        p = self.num_outputs

        if self.A.shape != (n, n):
            raise ValueError(f"A must be square, got shape {self.A.shape}")
        if self.B.shape != (n, m):
            raise ValueError(f"B shape {self.B.shape} inconsistent with A ({n}x{n}) and {m} inputs")
        if self.C.shape != (p, n):
            raise ValueError(f"C shape {self.C.shape} inconsistent with {p} outputs and {n} states")
        if self.D.shape != (p, m):
            raise ValueError(f"D shape {self.D.shape} inconsistent with {p} outputs and {m} inputs")

    @property
    def num_states(self) -> int:
        """Number of state variables (n)."""
        return self.A.shape[0]

    @property
    def num_inputs(self) -> int:
        """Number of control inputs (m)."""
        return self.B.shape[1]

    @property
    def num_outputs(self) -> int:
        """Number of outputs (p)."""
        return self.C.shape[0]

    @property
    def poles(self) -> np.ndarray:
        """Eigenvalues of A (system poles)."""
        return np.linalg.eigvals(self.A)

    @property
    def is_stable(self) -> bool:
        """
        Check if the continuous-time system is stable.

        A continuous-time system is stable if all poles have negative real parts.
        """
        return bool(np.all(np.real(self.poles) < 0))

    @property
    def is_marginally_stable(self) -> bool:
        """
        Check if poles are in the left half-plane (including imaginary axis).
        """
        return bool(np.all(np.real(self.poles) <= 0))

    def is_controllable(self, tol: float = 1e-10) -> bool:
        """
        Check controllability using the controllability matrix rank test.

        System is controllable if rank([B, AB, A^2B, ..., A^(n-1)B]) = n
        """
        return np.linalg.matrix_rank(self.controllability_matrix, tol=tol) == self.num_states

    def is_observable(self, tol: float = 1e-10) -> bool:
        """
        Check observability using the observability matrix rank test.

        System is observable if rank([C; CA; CA^2; ...; CA^(n-1)]) = n
        """
        return np.linalg.matrix_rank(self.observability_matrix, tol=tol) == self.num_states

    @property
    def controllability_matrix(self) -> np.ndarray:
        """
        Controllability matrix: [B, AB, A^2B, ..., A^(n-1)B]
        """
        n = self.num_states
        C_mat = self.B.copy()
        Ak_B = self.B.copy()
        for _ in range(1, n):
            Ak_B = self.A @ Ak_B
            C_mat = np.hstack([C_mat, Ak_B])
        return C_mat

    @property
    def observability_matrix(self) -> np.ndarray:
        """
        Observability matrix: [C; CA; CA^2; ...; CA^(n-1)]
        """
        n = self.num_states
        O_mat = self.C.copy()
        CA_k = self.C.copy()
        for _ in range(1, n):
            CA_k = CA_k @ self.A
            O_mat = np.vstack([O_mat, CA_k])
        return O_mat

    def to_discrete(self, dt: float, method: str = "zoh") -> "StateSpaceModel":
        """
        Convert to discrete-time state-space model.

        Args:
            dt: Sample time in seconds
            method: Discretization method ('zoh', 'bilinear', 'euler')

        Returns:
            Discrete-time StateSpaceModel (Ad, Bd, Cd, Dd)
        """
        return discretize(self, dt, method)

    def simulate(
        self,
        t: ArrayLike,
        u: Optional[ArrayLike] = None,
        x0: Optional[ArrayLike] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulate the system response.

        Args:
            t: Time vector
            u: Input signal (len(t) x m), defaults to zero input
            x0: Initial state, defaults to zero

        Returns:
            Tuple of (y, x) - output and state trajectories
        """
        try:
            from scipy.signal import lsim
            from scipy.signal import StateSpace as ScipySS
        except ImportError:
            raise ImportError("scipy required for simulation: pip install scipy")

        t = np.asarray(t)
        if x0 is None:
            x0 = np.zeros(self.num_states)
        if u is None:
            u = np.zeros((len(t), self.num_inputs))

        sys = ScipySS(self.A, self.B, self.C, self.D)
        _, y, x = lsim(sys, U=u, T=t, X0=x0)
        return y, x

    def __repr__(self) -> str:
        return (
            f"StateSpaceModel(n={self.num_states}, m={self.num_inputs}, p={self.num_outputs}, "
            f"stable={self.is_stable})"
        )


def discretize(
    sys: StateSpaceModel,
    dt: float,
    method: str = "zoh",
) -> StateSpaceModel:
    """
    Discretize a continuous-time state-space model.

    Args:
        sys: Continuous-time StateSpaceModel
        dt: Sample time in seconds
        method: 'zoh' (zero-order hold), 'bilinear' (Tustin), or 'euler'

    Returns:
        Discrete-time StateSpaceModel
    """
    A, B, C, D = sys.A, sys.B, sys.C, sys.D
    n = sys.num_states

    if method == "euler":
        # Forward Euler: Ad = I + A*dt, Bd = B*dt
        Ad = np.eye(n) + A * dt
        Bd = B * dt
        Cd = C.copy()
        Dd = D.copy()

    elif method == "bilinear":
        # Tustin/bilinear: (I - A*dt/2)^-1 * (I + A*dt/2)
        I = np.eye(n)
        A_half = A * (dt / 2)
        inv_term = np.linalg.inv(I - A_half)
        Ad = inv_term @ (I + A_half)
        Bd = inv_term @ B * dt
        Cd = C.copy()
        Dd = D.copy()

    elif method == "zoh":
        # Zero-order hold (exact discretization)
        try:
            from scipy.linalg import expm
        except ImportError:
            raise ImportError("scipy required for ZOH discretization: pip install scipy")

        # Build augmented matrix [A, B; 0, 0] and take matrix exponential
        m = sys.num_inputs
        aug = np.zeros((n + m, n + m))
        aug[:n, :n] = A * dt
        aug[:n, n:] = B * dt

        exp_aug = expm(aug)
        Ad = exp_aug[:n, :n]
        Bd = exp_aug[:n, n:]
        Cd = C.copy()
        Dd = D.copy()

    else:
        raise ValueError(f"Unknown discretization method: {method}")

    return StateSpaceModel(Ad, Bd, Cd, Dd)
