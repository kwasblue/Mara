"""Tests for the control design module."""

import numpy as np
import pytest

from mara_host.control import (
    StateSpaceModel,
    discretize,
    lqr,
    lqr_discrete,
    pole_placement,
    observer_gains,
    acker,
)
from mara_host.control.design import (
    check_stability,
    reference_gain,
    integral_gain,
    lqe,
)

# Skip tests requiring scipy if not installed
try:
    import scipy
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

requires_scipy = pytest.mark.skipif(not HAS_SCIPY, reason="scipy not installed")


# ============================================================================
# StateSpaceModel Tests
# ============================================================================


class TestStateSpaceModel:
    """Tests for StateSpaceModel class."""

    def test_create_model(self):
        """Test basic model creation."""
        A = [[0, 1], [-10, -0.5]]
        B = [[0], [1]]
        C = [[1, 0]]

        model = StateSpaceModel(A, B, C)

        assert model.num_states == 2
        assert model.num_inputs == 1
        assert model.num_outputs == 1
        assert model.D.shape == (1, 1)
        assert np.allclose(model.D, 0)

    def test_create_with_D(self):
        """Test model creation with feedthrough."""
        A = np.eye(2)
        B = np.array([[1], [0]])
        C = np.array([[1, 0]])
        D = np.array([[0.5]])

        model = StateSpaceModel(A, B, C, D)
        assert np.allclose(model.D, [[0.5]])

    def test_dimension_validation(self):
        """Test that dimension mismatches raise errors."""
        A = np.eye(2)
        B = np.array([[1, 0, 0]])  # Wrong shape

        with pytest.raises(ValueError):
            StateSpaceModel(A, B, [[1, 0]])

    def test_poles(self):
        """Test pole computation."""
        # Mass-spring-damper: poles at -0.25 +/- 3.12j
        A = np.array([[0, 1], [-10, -0.5]])
        B = np.array([[0], [1]])
        C = np.array([[1, 0]])

        model = StateSpaceModel(A, B, C)
        poles = model.poles

        assert len(poles) == 2
        # Check real part is negative (stable)
        assert np.all(np.real(poles) < 0)

    def test_stability_check(self):
        """Test stability detection."""
        # Stable system
        A_stable = np.array([[0, 1], [-10, -0.5]])
        model_stable = StateSpaceModel(A_stable, [[0], [1]], [[1, 0]])
        assert model_stable.is_stable

        # Unstable system (positive eigenvalue)
        A_unstable = np.array([[0, 1], [10, 0.5]])
        model_unstable = StateSpaceModel(A_unstable, [[0], [1]], [[1, 0]])
        assert not model_unstable.is_stable

    def test_controllability(self):
        """Test controllability check."""
        # Controllable system
        A = np.array([[0, 1], [-2, -3]])
        B = np.array([[0], [1]])
        model = StateSpaceModel(A, B, [[1, 0]])
        assert model.is_controllable()

        # Uncontrollable: B has zeros where A can't reach
        A_unc = np.array([[1, 0], [0, 2]])
        B_unc = np.array([[1], [0]])
        model_unc = StateSpaceModel(A_unc, B_unc, [[1, 1]])
        assert not model_unc.is_controllable()

    def test_observability(self):
        """Test observability check."""
        # Observable system
        A = np.array([[0, 1], [-2, -3]])
        C = np.array([[1, 0]])
        model = StateSpaceModel(A, [[0], [1]], C)
        assert model.is_observable()

        # Unobservable: C can't see second state
        A_uno = np.array([[1, 0], [0, 2]])
        C_uno = np.array([[1, 0]])
        model_uno = StateSpaceModel(A_uno, [[1], [1]], C_uno)
        assert not model_uno.is_observable()


@requires_scipy
class TestDiscretization:
    """Tests for discretization functions."""

    def test_euler_discretization(self):
        """Test forward Euler discretization."""
        A = np.array([[0, 1], [-10, -1]])
        B = np.array([[0], [1]])
        C = np.array([[1, 0]])
        model = StateSpaceModel(A, B, C)

        dt = 0.01
        model_d = discretize(model, dt, method="euler")

        # Euler: Ad = I + A*dt
        expected_Ad = np.eye(2) + A * dt
        assert np.allclose(model_d.A, expected_Ad)
        assert np.allclose(model_d.B, B * dt)

    def test_zoh_discretization(self):
        """Test zero-order hold discretization."""
        A = np.array([[0, 1], [-10, -1]])
        B = np.array([[0], [1]])
        C = np.array([[1, 0]])
        model = StateSpaceModel(A, B, C)

        dt = 0.01
        model_d = discretize(model, dt, method="zoh")

        # ZOH preserves stability
        assert model_d.num_states == 2
        # All discrete poles should be inside unit circle for stable system
        poles = model_d.poles
        assert np.all(np.abs(poles) < 1)

    def test_bilinear_discretization(self):
        """Test bilinear (Tustin) discretization."""
        A = np.array([[0, 1], [-10, -1]])
        B = np.array([[0], [1]])
        C = np.array([[1, 0]])
        model = StateSpaceModel(A, B, C)

        dt = 0.01
        model_d = discretize(model, dt, method="bilinear")

        # Bilinear preserves stability
        poles = model_d.poles
        assert np.all(np.abs(poles) < 1)


# ============================================================================
# LQR Tests
# ============================================================================


@requires_scipy
class TestLQR:
    """Tests for LQR design functions."""

    def test_lqr_basic(self):
        """Test basic LQR gain computation."""
        A = np.array([[0, 1], [-2, -3]])
        B = np.array([[0], [1]])
        Q = np.diag([10, 1])
        R = np.array([[1]])

        K, S, E = lqr(A, B, Q, R)

        # K should be (1, 2)
        assert K.shape == (1, 2)

        # Closed-loop should be stable (all poles have negative real part)
        assert np.all(np.real(E) < 0)

        # Check Riccati equation is satisfied (approximately)
        # A'S + SA - SBR^-1B'S + Q = 0
        residual = A.T @ S + S @ A - S @ B @ np.linalg.inv(R) @ B.T @ S + Q
        assert np.allclose(residual, 0, atol=1e-8)

    def test_lqr_higher_Q_faster_response(self):
        """Test that higher Q leads to faster response (poles further left)."""
        A = np.array([[0, 1], [-2, -3]])
        B = np.array([[0], [1]])
        R = np.array([[1]])

        Q_low = np.diag([1, 1])
        Q_high = np.diag([100, 1])

        _, _, E_low = lqr(A, B, Q_low, R)
        _, _, E_high = lqr(A, B, Q_high, R)

        # Higher Q should push poles further into LHP
        max_real_low = np.max(np.real(E_low))
        max_real_high = np.max(np.real(E_high))
        assert max_real_high < max_real_low

    def test_lqr_discrete(self):
        """Test discrete-time LQR."""
        Ad = np.array([[0.9, 0.1], [-0.1, 0.8]])
        Bd = np.array([[0.01], [0.1]])
        Q = np.diag([10, 1])
        R = np.array([[1]])

        K, S, E = lqr_discrete(Ad, Bd, Q, R)

        # Closed-loop poles should be inside unit circle
        A_cl = Ad - Bd @ K
        poles = np.linalg.eigvals(A_cl)
        assert np.all(np.abs(poles) < 1)


# ============================================================================
# Pole Placement Tests
# ============================================================================


@requires_scipy
class TestPolePlacement:
    """Tests for pole placement functions."""

    def test_pole_placement_basic(self):
        """Test basic pole placement."""
        A = np.array([[0, 1], [-2, -3]])
        B = np.array([[0], [1]])
        desired_poles = np.array([-5, -6])

        K = pole_placement(A, B, desired_poles)

        # Check closed-loop poles match desired
        A_cl = A - B @ K
        actual_poles = np.sort(np.linalg.eigvals(A_cl))
        expected_poles = np.sort(desired_poles)
        assert np.allclose(actual_poles, expected_poles, atol=1e-6)

    def test_pole_placement_complex(self):
        """Test pole placement with complex poles."""
        A = np.array([[0, 1], [-2, -3]])
        B = np.array([[0], [1]])
        desired_poles = np.array([-5 + 5j, -5 - 5j])

        K = pole_placement(A, B, desired_poles)

        A_cl = A - B @ K
        actual_poles = np.linalg.eigvals(A_cl)

        # Check poles match (complex conjugate pairs)
        assert np.allclose(np.sort(np.real(actual_poles)), [-5, -5], atol=1e-6)
        assert np.allclose(np.sort(np.abs(np.imag(actual_poles))), [5, 5], atol=1e-6)

    def test_acker_matches_pole_placement(self):
        """Test Ackermann's formula gives same result as place_poles for SISO."""
        A = np.array([[0, 1], [-2, -3]])
        B = np.array([[0], [1]])
        desired_poles = np.array([-5, -6])

        K_acker = acker(A, B, desired_poles)
        K_pp = pole_placement(A, B, desired_poles)

        # Should give same gain (within tolerance)
        assert np.allclose(K_acker, K_pp, atol=1e-6)


# ============================================================================
# Observer Gain Tests
# ============================================================================


@requires_scipy
class TestObserverGains:
    """Tests for observer gain design."""

    def test_observer_gains_basic(self):
        """Test basic observer gain computation."""
        A = np.array([[0, 1], [-2, -3]])
        C = np.array([[1, 0]])
        desired_poles = np.array([-10, -12])

        L = observer_gains(A, C, desired_poles)

        # Check observer poles match desired
        A_obs = A - L @ C
        actual_poles = np.sort(np.linalg.eigvals(A_obs))
        expected_poles = np.sort(desired_poles)
        assert np.allclose(actual_poles, expected_poles, atol=1e-6)

    def test_observer_faster_than_controller(self):
        """Test observer poles can be placed faster than controller."""
        A = np.array([[0, 1], [-2, -3]])
        B = np.array([[0], [1]])
        C = np.array([[1, 0]])

        # Controller poles
        ctrl_poles = np.array([-5, -6])
        K = pole_placement(A, B, ctrl_poles)

        # Observer poles (5x faster)
        obs_poles = np.array([-25, -30])
        L = observer_gains(A, C, obs_poles)

        # Check both are stable and observer is faster
        A_cl = A - B @ K
        A_obs = A - L @ C

        ctrl_max_real = np.max(np.real(np.linalg.eigvals(A_cl)))
        obs_max_real = np.max(np.real(np.linalg.eigvals(A_obs)))

        assert ctrl_max_real < 0
        assert obs_max_real < 0
        assert obs_max_real < ctrl_max_real  # Observer faster

    def test_lqe_kalman_filter(self):
        """Test LQE (Kalman filter) gain design."""
        A = np.array([[0, 1], [-2, -3]])
        C = np.array([[1, 0]])
        Q = np.diag([0.1, 1.0])  # Process noise
        R = np.array([[0.1]])    # Measurement noise

        L, P, E = lqe(A, C, Q, R)

        # Observer should be stable
        assert np.all(np.real(E) < 0)

        # L should have correct shape
        assert L.shape == (2, 1)


# ============================================================================
# Utility Function Tests
# ============================================================================


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_check_stability_continuous(self):
        """Test stability check for continuous-time systems."""
        A = np.array([[0, 1], [-2, -3]])
        B = np.array([[0], [1]])
        K = np.array([[8, 2]])  # Some stabilizing gain

        is_stable, poles = check_stability(A, B, K, continuous=True)
        assert is_stable
        assert np.all(np.real(poles) < 0)

    def test_check_stability_discrete(self):
        """Test stability check for discrete-time systems."""
        Ad = np.array([[0.9, 0.1], [-0.1, 0.8]])
        Bd = np.array([[0.01], [0.1]])
        K = np.array([[0.5, 0.1]])

        is_stable, poles = check_stability(Ad, Bd, K, continuous=False)
        assert is_stable
        assert np.all(np.abs(poles) < 1)

    def test_reference_gain(self):
        """Test reference gain computation."""
        A = np.array([[0, 1], [-2, -3]])
        B = np.array([[0], [1]])
        C = np.array([[1, 0]])
        K = np.array([[8, 2]])

        Kr = reference_gain(A, B, C, K)

        # Kr should be scalar-like for SISO
        assert Kr.shape == (1, 1)

    def test_integral_gain(self):
        """Test integral gain matrix creation."""
        Ki = integral_gain(n_states=2, n_outputs=1, ki_diag=0.5)
        assert Ki.shape == (1, 1)
        assert Ki[0, 0] == 0.5

        # Multiple outputs
        Ki_multi = integral_gain(n_states=3, n_outputs=2, ki_diag=[0.3, 0.7])
        assert Ki_multi.shape == (2, 2)
        assert np.allclose(np.diag(Ki_multi), [0.3, 0.7])


# ============================================================================
# Integration Tests
# ============================================================================


@requires_scipy
class TestIntegration:
    """Integration tests for complete design workflow."""

    def test_mass_spring_damper_design(self):
        """Test complete design for mass-spring-damper system."""
        # System parameters
        M, B_damp, K_spring = 1.0, 0.5, 10.0

        # State-space model
        A = np.array([[0, 1], [-K_spring / M, -B_damp / M]])
        B = np.array([[0], [1 / M]])
        C = np.array([[1, 0]])

        model = StateSpaceModel(A, B, C)

        # Verify system properties
        assert model.is_controllable()
        assert model.is_observable()
        assert model.is_stable  # Passive system is stable

        # LQR design
        Q = np.diag([100, 1])
        R = np.array([[0.1]])
        K_lqr, _, E_ctrl = lqr(A, B, Q, R)

        # Observer design (5x faster than slowest controller pole)
        # Use real distinct poles to avoid scipy's complex pole handling
        slowest_pole = np.max(np.real(E_ctrl))
        obs_poles = np.array([5 * slowest_pole, 6 * slowest_pole])
        L = observer_gains(A, C, obs_poles)

        # Verify closed-loop stability
        is_stable, _ = check_stability(A, B, K_lqr)
        assert is_stable

        # Discretize for MCU
        dt = 0.01  # 100 Hz
        model_d = model.to_discrete(dt, method="zoh")
        assert np.all(np.abs(model_d.poles) < 1)  # Discrete stable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
