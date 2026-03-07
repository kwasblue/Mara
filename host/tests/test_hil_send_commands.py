# tests/test_hil_commands.py

import pytest

pytestmark = [pytest.mark.hil, pytest.mark.asyncio]


class TestSafety:
    async def test_heartbeat(self, hil):
        await hil.assert_ok("CMD_HEARTBEAT")

    async def test_clear_estop(self, hil):
        await hil.assert_ok("CMD_CLEAR_ESTOP")

    async def test_arm_disarm(self, hil):
        await hil.assert_ok("CMD_ARM")
        await hil.assert_ok("CMD_DISARM")

    async def test_full_state_cycle(self, hil):
        await hil.assert_ok("CMD_ARM")
        await hil.assert_ok("CMD_ACTIVATE")
        await hil.assert_ok("CMD_DEACTIVATE")
        await hil.assert_ok("CMD_DISARM")


class TestRates:
    async def test_get_rates(self, hil):
        await hil.assert_ok("CMD_GET_RATES")

    @pytest.mark.parametrize("hz", [10, 50, 100])
    async def test_ctrl_set_rate(self, hil, hz):
        await hil.assert_ok("CMD_CTRL_SET_RATE", {"hz": hz})

    @pytest.mark.parametrize("hz", [10, 50, 100])
    async def test_safety_set_rate(self, hil, hz):
        await hil.assert_ok("CMD_SAFETY_SET_RATE", {"hz": hz})

    @pytest.mark.parametrize("hz", [1, 10, 50])
    async def test_telem_set_rate(self, hil, hz):
        await hil.assert_ok("CMD_TELEM_SET_RATE", {"hz": hz})


class TestControlSignals:

    
    async def test_define_signal(self, hil):
        await hil.assert_ok("CMD_CTRL_SIGNAL_DEFINE", {
            "id": 100, "name": "test_ref", "signal_kind": "REF", "initial": 0.0
        })

    async def test_signal_set_get(self, hil):
        await hil.assert_ok("CMD_CTRL_SIGNAL_DEFINE", {
            "id": 110, "name": "sg_test", "signal_kind": "REF", "initial": 0.0
        })
        await hil.assert_ok("CMD_CTRL_SIGNAL_SET", {"id": 110, "value": 42.5})
        await hil.assert_ok("CMD_CTRL_SIGNAL_GET", {"id": 110})

    async def test_signals_list(self, hil):
        await hil.assert_ok("CMD_CTRL_SIGNALS_LIST")


class TestControlSlots:
    @pytest.fixture
    async def setup(self, hil):
        await hil.clear_signals()
        yield
    
    @pytest.fixture
    async def slot(self, hil):
        """Configure slot 0 with signals."""
        # Define signals first
        for sig in [
            {"id": 200, "name": "s_ref", "signal_kind": "REF", "initial": 0.0},
            {"id": 201, "name": "s_meas", "signal_kind": "MEAS", "initial": 0.0},
            {"id": 202, "name": "s_out", "signal_kind": "OUT", "initial": 0.0},
        ]:
            await hil.assert_ok("CMD_CTRL_SIGNAL_DEFINE", sig)
        
        # Configure slot
        await hil.assert_ok("CMD_CTRL_SLOT_CONFIG", {
            "slot": 0,
            "controller_type": "PID",
            "rate_hz": 100,
            "ref_id": 200,
            "meas_id": 201,
            "out_id": 202,
        })
        
        return 0 

    async def test_slot_enable(self, hil, slot):
        await hil.assert_ok("CMD_CTRL_SLOT_ENABLE", {"slot": slot, "enable": True})

    async def test_slot_reset(self, hil, slot):
        await hil.assert_ok("CMD_CTRL_SLOT_RESET", {"slot": slot})

    async def test_slot_set_param(self, hil, slot):
        await hil.assert_ok("CMD_CTRL_SLOT_SET_PARAM", {"slot": slot, "key": "kp", "value": 1.0})

    async def test_slot_status(self, hil, slot):
        await hil.assert_ok("CMD_CTRL_SLOT_STATUS", {"slot": slot})


class TestGPIO:
    async def test_register_write_read_toggle(self, hil):
        await hil.assert_ok("CMD_GPIO_REGISTER_CHANNEL", {"channel": 0, "pin": 2, "mode": "output"})
        await hil.assert_ok("CMD_GPIO_WRITE", {"channel": 0, "value": 1})
        await hil.assert_ok("CMD_GPIO_READ", {"channel": 0})
        await hil.assert_ok("CMD_GPIO_TOGGLE", {"channel": 0})


class TestPWM:
    async def test_pwm_set(self, hil):
        await hil.assert_ok("CMD_PWM_SET", {"channel": 0, "duty": 0.5, "freq_hz": 1000.0})


class TestLED:
    async def test_led_on_off(self, hil):
        await hil.assert_ok("CMD_LED_ON")
        await hil.assert_ok("CMD_LED_OFF")


class TestServo:
    async def test_attach_detach(self, hil):
        await hil.assert_ok("CMD_SERVO_ATTACH", {"servo_id": 0, "channel": 0, "min_us": 1000, "max_us": 2000})
        await hil.assert_ok("CMD_SERVO_DETACH", {"servo_id": 0})

    @pytest.mark.motion
    async def test_set_angle(self, active_robot, hil):
        await hil.assert_ok("CMD_SERVO_ATTACH", {"servo_id": 0, "channel": 0, "min_us": 1000, "max_us": 2000})
        await hil.assert_ok("CMD_SERVO_SET_ANGLE", {"servo_id": 0, "angle_deg": 90})


class TestStepper:
    async def test_enable_stop(self, hil):
        await hil.assert_ok("CMD_STEPPER_ENABLE", {"motor_id": 0, "enable": True})
        await hil.assert_ok("CMD_STEPPER_STOP", {"motor_id": 0})

    @pytest.mark.motion
    async def test_move_rel(self, active_robot, hil):
        await hil.assert_ok("CMD_STEPPER_ENABLE", {"motor_id": 0, "enable": True})
        await hil.assert_ok("CMD_STEPPER_MOVE_REL", {"motor_id": 0, "steps": 50, "speed_steps_s": 1000.0})


class TestEncoder:
    async def test_attach_read_reset(self, hil):
        await hil.assert_ok("CMD_ENCODER_ATTACH", {"encoder_id": 0, "pin_a": 32, "pin_b": 33})
        await hil.assert_ok("CMD_ENCODER_READ", {"encoder_id": 0})
        await hil.assert_ok("CMD_ENCODER_RESET", {"encoder_id": 0})


class TestDCMotor:
    async def test_stop(self, hil):
        await hil.assert_ok("CMD_DC_STOP", {"motor_id": 0})

    async def test_pid_gains(self, hil):
        await hil.assert_ok("CMD_DC_SET_VEL_GAINS", {"motor_id": 0, "kp": 1.0, "ki": 0.1, "kd": 0.01})

    @pytest.mark.motion
    async def test_set_speed(self, active_robot, hil):
        await hil.assert_ok("CMD_DC_SET_SPEED", {"motor_id": 0, "speed": 0.1})
        await hil.assert_ok("CMD_DC_STOP", {"motor_id": 0})


class TestMotion:
    @pytest.mark.motion
    async def test_set_vel(self, active_robot, hil):
        await hil.assert_ok("CMD_SET_VEL", {"vx": 0.0, "omega": 0.0})


class TestTelemetry:
    async def test_set_interval(self, hil):
        await hil.assert_ok("CMD_TELEM_SET_INTERVAL", {"interval_ms": 100})


class TestLogging:
    async def test_set_log_level(self, hil):
        await hil.assert_ok("CMD_SET_LOG_LEVEL", {"level": "info"})

# ------------------------------------------------------------------------------
# Observer Tests
# ------------------------------------------------------------------------------

class TestObserver:
    """Test observer configuration and operation."""
        
    async def setup(self, hil):
        await hil.clear_signals()
        yield
    
    @pytest.fixture
    async def observer_signals(self, hil):
        """Define signals needed for observer testing."""
        # Control input signal
        await hil.assert_ok("CMD_CTRL_SIGNAL_DEFINE", {
            "id": 100, "name": "motor_cmd", "signal_kind": "OUT", "initial": 0.0
        })
        # Measurement signal
        await hil.assert_ok("CMD_CTRL_SIGNAL_DEFINE", {
            "id": 101, "name": "theta_meas", "signal_kind": "MEAS", "initial": 0.0
        })
        # Estimate signals
        await hil.assert_ok("CMD_CTRL_SIGNAL_DEFINE", {
            "id": 200, "name": "theta_est", "signal_kind": "MEAS", "initial": 0.0
        })
        await hil.assert_ok("CMD_CTRL_SIGNAL_DEFINE", {
            "id": 201, "name": "omega_est", "signal_kind": "MEAS", "initial": 0.0
        })
        return [100, 101, 200, 201]

    async def test_observer_config(self, hil, observer_signals):
        """Test observer configuration."""
        await hil.assert_ok("CMD_OBSERVER_CONFIG", {
            "slot": 0,
            "num_states": 2,
            "num_inputs": 1,
            "num_outputs": 1,
            "rate_hz": 200,
            "input_ids": [100],
            "output_ids": [101],
            "estimate_ids": [200, 201]
        })

    async def test_observer_set_matrices(self, hil, observer_signals):
        """Test setting observer matrices."""
        # Configure first
        await hil.assert_ok("CMD_OBSERVER_CONFIG", {
            "slot": 0,
            "num_states": 2,
            "num_inputs": 1,
            "num_outputs": 1,
            "rate_hz": 200,
            "input_ids": [100],
            "output_ids": [101],
            "estimate_ids": [200, 201]
        })
        
        # Set A matrix (2x2): [[0, 1], [0, -10]]
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0,
            "key": "A",
            "values": [0, 1, 0, -10]
        })
        
        # Set B matrix (2x1): [[0], [50]]
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0,
            "key": "B",
            "values": [0, 50]
        })
        
        # Set C matrix (1x2): [[1, 0]]
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0,
            "key": "C",
            "values": [1, 0]
        })
        
        # Set L matrix (2x1): [[50], [500]]
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0,
            "key": "L",
            "values": [50, 500]
        })

    async def test_observer_set_param_individual(self, hil, observer_signals):
        """Test setting individual matrix elements."""
        await hil.assert_ok("CMD_OBSERVER_CONFIG", {
            "slot": 0,
            "num_states": 2,
            "num_inputs": 1,
            "num_outputs": 1,
            "rate_hz": 200,
            "input_ids": [100],
            "output_ids": [101],
            "estimate_ids": [200, 201]
        })
        
        # Set A[0][1] = 1.0
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM", {
            "slot": 0,
            "key": "A01",
            "value": 1.0
        })
        
        # Set L[1][0] = 100.0
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM", {
            "slot": 0,
            "key": "L10",
            "value": 100.0
        })

    async def test_observer_enable_disable(self, hil, observer_signals):
        """Test enabling and disabling observer."""
        # Configure first
        await hil.assert_ok("CMD_OBSERVER_CONFIG", {
            "slot": 0,
            "num_states": 2,
            "num_inputs": 1,
            "num_outputs": 1,
            "rate_hz": 200,
            "input_ids": [100],
            "output_ids": [101],
            "estimate_ids": [200, 201]
        })
        
        # Enable
        await hil.assert_ok("CMD_OBSERVER_ENABLE", {"slot": 0, "enable": True})
        
        # Disable
        await hil.assert_ok("CMD_OBSERVER_ENABLE", {"slot": 0, "enable": False})

    async def test_observer_reset(self, hil, observer_signals):
        """Test resetting observer state."""
        await hil.assert_ok("CMD_OBSERVER_CONFIG", {
            "slot": 0,
            "num_states": 2,
            "num_inputs": 1,
            "num_outputs": 1,
            "rate_hz": 200,
            "input_ids": [100],
            "output_ids": [101],
            "estimate_ids": [200, 201]
        })
        
        await hil.assert_ok("CMD_OBSERVER_RESET", {"slot": 0})

    async def test_observer_status(self, hil, observer_signals):
        """Test getting observer status."""
        await hil.assert_ok("CMD_OBSERVER_CONFIG", {
            "slot": 0,
            "num_states": 2,
            "num_inputs": 1,
            "num_outputs": 1,
            "rate_hz": 200,
            "input_ids": [100],
            "output_ids": [101],
            "estimate_ids": [200, 201]
        })
        
        await hil.assert_ok("CMD_OBSERVER_STATUS", {"slot": 0})

    async def test_observer_full_setup(self, hil, observer_signals):
        """Test complete observer setup for DC motor velocity estimation."""
        # Configure
        await hil.assert_ok("CMD_OBSERVER_CONFIG", {
            "slot": 0,
            "num_states": 2,
            "num_inputs": 1,
            "num_outputs": 1,
            "rate_hz": 500,
            "input_ids": [100],
            "output_ids": [101],
            "estimate_ids": [200, 201]
        })
        
        # Set all matrices for a DC motor model
        # dθ/dt = ω
        # dω/dt = -10*ω + 50*u
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0, "key": "A", "values": [0, 1, 0, -10]
        })
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0, "key": "B", "values": [0, 50]
        })
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0, "key": "C", "values": [1, 0]
        })
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0, "key": "L", "values": [100, 500]
        })
        
        # Enable
        await hil.assert_ok("CMD_OBSERVER_ENABLE", {"slot": 0, "enable": True})
        
        # Check status
        await hil.assert_ok("CMD_OBSERVER_STATUS", {"slot": 0})

    async def test_observer_enable_fails_without_config(self, hil):
        """Test that enabling unconfigured observer fails."""
        # Try to enable slot 3 which isn't configured
        await hil.assert_fails("CMD_OBSERVER_ENABLE", {
            "slot": 3,
            "enable": True
        })

    async def test_observer_with_controller(self, hil, observer_signals):
        """Test observer feeding a PID controller."""
        # Configure observer
        await hil.assert_ok("CMD_OBSERVER_CONFIG", {
            "slot": 0,
            "num_states": 2,
            "num_inputs": 1,
            "num_outputs": 1,
            "rate_hz": 500,
            "input_ids": [100],
            "output_ids": [101],
            "estimate_ids": [200, 201]
        })
        
        # Set matrices
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0, "key": "A", "values": [0, 1, 0, -10]
        })
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0, "key": "B", "values": [0, 50]
        })
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0, "key": "C", "values": [1, 0]
        })
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": 0, "key": "L", "values": [100, 500]
        })
        
        # Enable observer
        await hil.assert_ok("CMD_OBSERVER_ENABLE", {"slot": 0, "enable": True})
        
        # Define reference signal
        await hil.assert_ok("CMD_CTRL_SIGNAL_DEFINE", {
            "id": 300, "name": "omega_ref", "signal_kind": "REF", "initial": 0.0
        })
        
        # Configure PID to use observer's velocity estimate (signal 201)
        await hil.assert_ok("CMD_CTRL_SLOT_CONFIG", {
            "slot": 0,
            "controller_type": "PID",
            "rate_hz": 200,
            "ref_id": 300,      # Velocity setpoint
            "meas_id": 201,     # Observer's velocity estimate!
            "out_id": 100,      # Motor command
        })
        
        # Set PID gains
        await hil.assert_ok("CMD_CTRL_SLOT_SET_PARAM", {"slot": 0, "key": "kp", "value": 0.5})
        await hil.assert_ok("CMD_CTRL_SLOT_SET_PARAM", {"slot": 0, "key": "ki", "value": 1.0})
        await hil.assert_ok("CMD_CTRL_SLOT_SET_PARAM", {"slot": 0, "key": "kd", "value": 0.01})
        
        # Enable controller
        await hil.assert_ok("CMD_CTRL_SLOT_ENABLE", {"slot": 0, "enable": True})
        
        # Check both are running
        await hil.assert_ok("CMD_OBSERVER_STATUS", {"slot": 0})
        await hil.assert_ok("CMD_CTRL_SLOT_STATUS", {"slot": 0})


class TestObserverStateSpace:
    """Test observer with state-space controller (full state feedback)."""
    
    async def setup(self, hil):
        await hil.clear_signals()
        yield
    
    @pytest.fixture
    async def pendulum_signals(self, hil):
        """Define signals for inverted pendulum."""
        signals = [
            # Control output
            (100, "force_cmd", "OUT"),
            # Measurements
            (101, "theta_meas", "MEAS"),
            (102, "x_meas", "MEAS"),
            # Estimates
            (200, "theta_est", "MEAS"),
            (201, "theta_dot_est", "MEAS"),
            (202, "x_est", "MEAS"),
            (203, "x_dot_est", "MEAS"),
            # References
            (300, "theta_ref", "REF"),
            (301, "theta_dot_ref", "REF"),
            (302, "x_ref", "REF"),
            (303, "x_dot_ref", "REF"),
        ]
        
        for id, name, kind in signals:
            await hil.assert_ok("CMD_CTRL_SIGNAL_DEFINE", {
                "id": id, "name": name, "signal_kind": kind, "initial": 0.0
            })
        
        return signals

    async def test_pendulum_observer_config(self, hil, pendulum_signals):
        """Test 4-state observer configuration."""
        await hil.assert_ok("CMD_OBSERVER_CONFIG", {
            "slot": 0,
            "num_states": 4,
            "num_inputs": 1,
            "num_outputs": 2,
            "rate_hz": 500,
            "input_ids": [100],
            "output_ids": [101, 102],
            "estimate_ids": [200, 201, 202, 203]
        })

    async def test_pendulum_full_system(self, hil, pendulum_signals):
        """Test complete inverted pendulum control system."""
        # Configure observer
        await hil.assert_ok("CMD_OBSERVER_CONFIG", {
            "slot": 0,
            "num_states": 4,
            "num_inputs": 1,
            "num_outputs": 2,
            "rate_hz": 500,
            "input_ids": [100],
            "output_ids": [101, 102],
            "estimate_ids": [200, 201, 202, 203]
        })
        
        # Linearized pendulum model (simplified)
        # States: [θ, θ̇, x, ẋ]
        A = [
            0, 1, 0, 0,
            25, 0, 0, 0,   # g/L ≈ 25 for L=0.4m
            0, 0, 0, 1,
            -2.5, 0, 0, 0  # -m*g/(M) simplified
        ]
        B = [0, -2.5, 0, 1]  # Simplified
        C = [
            1, 0, 0, 0,  # Measure theta
            0, 0, 1, 0   # Measure x
        ]
        L = [
            40, 0,
            400, 0,
            0, 50,
            0, 600
        ]
        
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {"slot": 0, "key": "A", "values": A})
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {"slot": 0, "key": "B", "values": B})
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {"slot": 0, "key": "C", "values": C})
        await hil.assert_ok("CMD_OBSERVER_SET_PARAM_ARRAY", {"slot": 0, "key": "L", "values": L})
        
        await hil.assert_ok("CMD_OBSERVER_ENABLE", {"slot": 0, "enable": True})
        
        # Configure state-space controller
        await hil.assert_ok("CMD_CTRL_SLOT_CONFIG", {
            "slot": 0,
            "controller_type": "STATE_SPACE",
            "rate_hz": 200,
            "num_states": 4,
            "num_inputs": 1,
            "state_ids": [200, 201, 202, 203],  # Use observer estimates
            "ref_ids": [300, 301, 302, 303],
            "output_ids": [100],
        })
        
        # LQR gains (example values)
        K = [-100, -20, 10, 15]
        await hil.assert_ok("CMD_CTRL_SLOT_SET_PARAM_ARRAY", {"slot": 0, "key": "K", "values": K})
        
        await hil.assert_ok("CMD_CTRL_SLOT_ENABLE", {"slot": 0, "enable": True})
        
        # Verify both running
        await hil.assert_ok("CMD_OBSERVER_STATUS", {"slot": 0})
        await hil.assert_ok("CMD_CTRL_SLOT_STATUS", {"slot": 0})