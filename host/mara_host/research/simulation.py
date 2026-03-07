# mara_host/research/simulation.py
"""
Enhanced simulation models for robotics.

Includes:
- DC motor dynamics with back-EMF, friction
- Differential drive robot with realistic physics
- Sensor noise models (IMU, encoder, ultrasonic)
- Communication delay simulation
- Configurable robot parameters
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


# =============================================================================
# Noise Models
# =============================================================================

@dataclass
class GaussianNoise:
    """Gaussian noise model."""
    mean: float = 0.0
    std: float = 0.0

    def sample(self) -> float:
        return random.gauss(self.mean, self.std) if self.std > 0 else self.mean

    def add_to(self, value: float) -> float:
        return value + self.sample()


@dataclass
class IMUNoiseModel:
    """Noise model for IMU sensors."""
    # Accelerometer noise (g)
    accel_noise: GaussianNoise = field(default_factory=lambda: GaussianNoise(0, 0.01))
    accel_bias: np.ndarray = field(default_factory=lambda: np.zeros(3))

    # Gyroscope noise (rad/s)
    gyro_noise: GaussianNoise = field(default_factory=lambda: GaussianNoise(0, 0.001))
    gyro_bias: np.ndarray = field(default_factory=lambda: np.zeros(3))
    gyro_drift_rate: float = 1e-5  # rad/s per second

    def add_accel_noise(self, accel: np.ndarray) -> np.ndarray:
        """Add noise to accelerometer reading."""
        noise = np.array([self.accel_noise.sample() for _ in range(3)])
        return accel + noise + self.accel_bias

    def add_gyro_noise(self, gyro: np.ndarray, dt: float = 0.0) -> np.ndarray:
        """Add noise and drift to gyroscope reading."""
        noise = np.array([self.gyro_noise.sample() for _ in range(3)])
        # Simulate random walk drift
        if dt > 0:
            self.gyro_bias += np.random.randn(3) * self.gyro_drift_rate * dt
        return gyro + noise + self.gyro_bias


@dataclass
class EncoderNoiseModel:
    """Noise model for wheel encoders."""
    quantization_error: bool = True  # Encoder has discrete counts
    counts_per_rev: int = 1000
    missed_count_prob: float = 0.0  # Probability of missing a count

    def quantize(self, angle_rad: float) -> int:
        """Convert angle to encoder counts with quantization."""
        counts = int(angle_rad * self.counts_per_rev / (2 * np.pi))

        # Simulate missed counts
        if self.missed_count_prob > 0 and random.random() < self.missed_count_prob:
            counts += random.choice([-1, 1])

        return counts


@dataclass
class UltrasonicNoiseModel:
    """Noise model for ultrasonic sensors."""
    noise: GaussianNoise = field(default_factory=lambda: GaussianNoise(0, 0.02))  # 2cm std
    min_range: float = 0.02  # 2cm minimum
    max_range: float = 4.0   # 4m maximum
    multipath_prob: float = 0.01  # Probability of multipath error

    def add_noise(self, distance: float) -> float:
        """Add noise to distance measurement."""
        if distance < self.min_range:
            return self.min_range
        if distance > self.max_range:
            return self.max_range

        # Multipath error (occasional large error)
        if random.random() < self.multipath_prob:
            return random.uniform(self.min_range, self.max_range)

        return np.clip(
            self.noise.add_to(distance),
            self.min_range,
            self.max_range
        )


# =============================================================================
# DC Motor Model
# =============================================================================

@dataclass
class DCMotorConfig:
    """DC motor configuration parameters."""
    # Electrical parameters
    R: float = 2.0          # Armature resistance (Ohms)
    L: float = 0.001        # Armature inductance (H)
    Kv: float = 0.01        # Back-EMF constant (V/(rad/s))
    Kt: float = 0.01        # Torque constant (N·m/A)

    # Mechanical parameters
    J: float = 0.001        # Rotor inertia (kg·m²)
    b: float = 0.0001       # Viscous friction (N·m·s/rad)
    Kf: float = 0.0         # Coulomb friction (N·m)

    # Limits
    max_voltage: float = 12.0
    max_current: float = 10.0
    max_velocity: float = 100.0  # rad/s


class DCMotor:
    """
    DC motor simulation with electrical and mechanical dynamics.

    State: [current, velocity]
    """

    def __init__(self, config: DCMotorConfig):
        self.cfg = config
        self.current = 0.0  # Armature current (A)
        self.velocity = 0.0  # Angular velocity (rad/s)
        self.position = 0.0  # Angular position (rad)

    def step(self, voltage: float, load_torque: float, dt: float) -> Dict[str, float]:
        """
        Simulate one time step.

        Args:
            voltage: Applied voltage (V)
            load_torque: External load torque (N·m)
            dt: Time step (seconds)

        Returns:
            Dictionary with motor state
        """
        cfg = self.cfg

        # Clamp voltage
        voltage = np.clip(voltage, -cfg.max_voltage, cfg.max_voltage)

        # Electrical dynamics: L*di/dt = V - R*i - Kv*w
        back_emf = cfg.Kv * self.velocity
        di_dt = (voltage - cfg.R * self.current - back_emf) / max(cfg.L, 1e-6)

        # Current limits
        new_current = np.clip(
            self.current + di_dt * dt,
            -cfg.max_current,
            cfg.max_current
        )

        # Motor torque
        motor_torque = cfg.Kt * new_current

        # Friction torque
        if abs(self.velocity) > 1e-6:
            friction_torque = cfg.Kf * np.sign(self.velocity) + cfg.b * self.velocity
        else:
            # Static friction at zero velocity
            friction_torque = np.clip(motor_torque - load_torque, -cfg.Kf, cfg.Kf)

        # Mechanical dynamics: J*dw/dt = tau_motor - tau_friction - tau_load
        net_torque = motor_torque - friction_torque - load_torque
        dw_dt = net_torque / cfg.J

        # Update state
        self.current = new_current
        self.velocity = np.clip(
            self.velocity + dw_dt * dt,
            -cfg.max_velocity,
            cfg.max_velocity
        )
        self.position += self.velocity * dt

        return {
            "current": self.current,
            "velocity": self.velocity,
            "position": self.position,
            "torque": motor_torque,
        }

    def reset(self):
        """Reset motor state."""
        self.current = 0.0
        self.velocity = 0.0
        self.position = 0.0


# =============================================================================
# Differential Drive Robot
# =============================================================================

@dataclass
class DiffDriveConfig:
    """Differential drive robot configuration."""
    wheel_radius: float = 0.05      # Wheel radius (m)
    wheel_base: float = 0.2         # Distance between wheels (m)
    robot_mass: float = 2.0         # Robot mass (kg)
    wheel_inertia: float = 0.001    # Wheel + motor inertia (kg·m²)

    # Motor configuration (same for both motors)
    motor_config: DCMotorConfig = field(default_factory=DCMotorConfig)

    # Velocity limits
    max_linear_vel: float = 1.0     # m/s
    max_angular_vel: float = 3.0    # rad/s

    # Acceleration limits
    max_linear_accel: float = 2.0   # m/s²
    max_angular_accel: float = 6.0  # rad/s²


class DiffDriveRobot:
    """
    Differential drive robot simulation with realistic physics.

    State: [x, y, theta, vx, omega]
    """

    def __init__(
        self,
        config: DiffDriveConfig,
        imu_noise: Optional[IMUNoiseModel] = None,
        encoder_noise: Optional[EncoderNoiseModel] = None,
    ):
        self.cfg = config
        self.imu_noise = imu_noise or IMUNoiseModel()
        self.encoder_noise = encoder_noise or EncoderNoiseModel()

        # Robot pose
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        # Velocities
        self.vx = 0.0      # Linear velocity (m/s)
        self.omega = 0.0   # Angular velocity (rad/s)

        # Motor models
        self.left_motor = DCMotor(config.motor_config)
        self.right_motor = DCMotor(config.motor_config)

        # Encoder state
        self.left_encoder = 0
        self.right_encoder = 0

    def set_velocity(self, vx: float, omega: float):
        """Set target velocity (open-loop, instant)."""
        self.vx = np.clip(vx, -self.cfg.max_linear_vel, self.cfg.max_linear_vel)
        self.omega = np.clip(omega, -self.cfg.max_angular_vel, self.cfg.max_angular_vel)

    def set_motor_voltages(self, left_voltage: float, right_voltage: float, dt: float):
        """
        Set motor voltages directly (for low-level control simulation).

        Returns wheel velocities.
        """
        # Step motors
        left_state = self.left_motor.step(left_voltage, 0.0, dt)
        right_state = self.right_motor.step(right_voltage, 0.0, dt)

        # Convert wheel velocities to robot velocities
        left_wheel_vel = left_state["velocity"] * self.cfg.wheel_radius
        right_wheel_vel = right_state["velocity"] * self.cfg.wheel_radius

        self.vx = (left_wheel_vel + right_wheel_vel) / 2
        self.omega = (right_wheel_vel - left_wheel_vel) / self.cfg.wheel_base

        return left_wheel_vel, right_wheel_vel

    def step(self, dt: float) -> Dict[str, Any]:
        """
        Simulate one time step.

        Uses current velocity commands to update pose.
        """
        # Apply acceleration limits (simple rate limiter)
        # For more realistic simulation, use motor model instead

        # Update pose using differential drive kinematics
        if abs(self.omega) < 1e-6:
            # Straight line motion
            self.x += self.vx * math.cos(self.theta) * dt
            self.y += self.vx * math.sin(self.theta) * dt
        else:
            # Arc motion
            radius = self.vx / self.omega
            self.x += radius * (math.sin(self.theta + self.omega * dt) - math.sin(self.theta))
            self.y += radius * (math.cos(self.theta) - math.cos(self.theta + self.omega * dt))
            self.theta += self.omega * dt

        # Normalize theta to [-pi, pi]
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))

        # Update encoder counts
        left_wheel_angle = (self.vx - self.omega * self.cfg.wheel_base / 2) / self.cfg.wheel_radius * dt
        right_wheel_angle = (self.vx + self.omega * self.cfg.wheel_base / 2) / self.cfg.wheel_radius * dt

        self.left_encoder += self.encoder_noise.quantize(left_wheel_angle)
        self.right_encoder += self.encoder_noise.quantize(right_wheel_angle)

        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """Get current robot state."""
        return {
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
            "vx": self.vx,
            "omega": self.omega,
            "left_encoder": self.left_encoder,
            "right_encoder": self.right_encoder,
        }

    def get_imu_reading(self) -> Dict[str, float]:
        """Get simulated IMU reading with noise."""
        # True values
        true_accel = np.array([0.0, 0.0, 9.81])  # Gravity only (assuming flat ground)
        true_gyro = np.array([0.0, 0.0, self.omega])

        # Add noise
        noisy_accel = self.imu_noise.add_accel_noise(true_accel)
        noisy_gyro = self.imu_noise.add_gyro_noise(true_gyro)

        return {
            "ax": noisy_accel[0],
            "ay": noisy_accel[1],
            "az": noisy_accel[2],
            "gx": noisy_gyro[0],
            "gy": noisy_gyro[1],
            "gz": noisy_gyro[2],
        }

    def get_encoder_velocities(self) -> Tuple[float, float]:
        """Get wheel velocities from encoder counts."""
        left_vel = self.left_motor.velocity * self.cfg.wheel_radius
        right_vel = self.right_motor.velocity * self.cfg.wheel_radius
        return left_vel, right_vel

    def reset(self, x: float = 0.0, y: float = 0.0, theta: float = 0.0):
        """Reset robot state."""
        self.x = x
        self.y = y
        self.theta = theta
        self.vx = 0.0
        self.omega = 0.0
        self.left_encoder = 0
        self.right_encoder = 0
        self.left_motor.reset()
        self.right_motor.reset()


# =============================================================================
# Communication Delay Simulation
# =============================================================================

@dataclass
class DelayConfig:
    """Communication delay configuration."""
    mean_delay_ms: float = 5.0
    std_delay_ms: float = 2.0
    jitter_ms: float = 1.0
    packet_loss_prob: float = 0.0
    max_delay_ms: float = 100.0


class DelaySimulator:
    """
    Simulates communication delays and packet loss.

    Maintains a queue of messages with delivery times.
    """

    def __init__(self, config: DelayConfig):
        self.cfg = config
        self.queue: List[Tuple[float, Any]] = []  # (delivery_time_s, message)
        self.current_time = 0.0

    def send(self, message: Any, current_time_s: float) -> bool:
        """
        Queue a message for delayed delivery.

        Returns:
            True if message was queued, False if lost
        """
        # Check for packet loss
        if random.random() < self.cfg.packet_loss_prob:
            return False

        # Calculate delay
        delay_ms = random.gauss(self.cfg.mean_delay_ms, self.cfg.std_delay_ms)
        delay_ms += random.uniform(-self.cfg.jitter_ms, self.cfg.jitter_ms)
        delay_ms = np.clip(delay_ms, 0, self.cfg.max_delay_ms)

        delivery_time = current_time_s + delay_ms / 1000

        self.queue.append((delivery_time, message))
        self.queue.sort(key=lambda x: x[0])

        return True

    def receive(self, current_time_s: float) -> List[Any]:
        """
        Get all messages that should be delivered by current_time.
        """
        delivered = []
        remaining = []

        for delivery_time, message in self.queue:
            if delivery_time <= current_time_s:
                delivered.append(message)
            else:
                remaining.append((delivery_time, message))

        self.queue = remaining
        return delivered

    def clear(self):
        """Clear all pending messages."""
        self.queue = []


# =============================================================================
# Simulation Runner
# =============================================================================

class SimulationRunner:
    """
    Runs a complete robot simulation loop.
    """

    def __init__(
        self,
        robot: DiffDriveRobot,
        controller: Optional[Callable[[Dict[str, Any]], Tuple[float, float]]] = None,
        dt: float = 0.01,
        delay_config: Optional[DelayConfig] = None,
    ):
        self.robot = robot
        self.controller = controller
        self.dt = dt
        self.delay = DelaySimulator(delay_config) if delay_config else None

        self.time = 0.0
        self.history: List[Dict[str, Any]] = []

    def step(self) -> Dict[str, Any]:
        """Run one simulation step."""
        state = self.robot.get_state()
        imu = self.robot.get_imu_reading()

        # Get control command
        if self.controller:
            vx, omega = self.controller({**state, **imu})

            # Apply delay if configured
            if self.delay:
                self.delay.send((vx, omega), self.time)
                commands = self.delay.receive(self.time)
                if commands:
                    vx, omega = commands[-1]  # Use most recent
                else:
                    vx, omega = 0.0, 0.0  # No command yet

            self.robot.set_velocity(vx, omega)

        # Step robot
        new_state = self.robot.step(self.dt)
        new_state["time"] = self.time
        new_state["imu"] = imu

        self.history.append(new_state)
        self.time += self.dt

        return new_state

    def run(self, duration_s: float) -> List[Dict[str, Any]]:
        """Run simulation for specified duration."""
        n_steps = int(duration_s / self.dt)

        for _ in range(n_steps):
            self.step()

        return self.history

    def reset(self):
        """Reset simulation."""
        self.robot.reset()
        self.time = 0.0
        self.history = []
        if self.delay:
            self.delay.clear()


# =============================================================================
# Simple Physics (backward compatible)
# =============================================================================

class DiffDrivePhysics:
    """
    Simple differential drive physics for backward compatibility.

    Use DiffDriveRobot for more realistic simulation.
    """

    def __init__(self):
        self.x = self.y = self.theta = 0.0
        self.vx = 0.0
        self.omega = 0.0

    def set_velocity(self, vx: float, omega: float):
        self.vx = float(vx)
        self.omega = float(omega)

    def step(self, dt: float):
        self.x += self.vx * math.cos(self.theta) * dt
        self.y += self.vx * math.sin(self.theta) * dt
        self.theta += self.omega * dt

    def imu(self) -> Dict[str, float]:
        return {"gz_dps": math.degrees(self.omega), "az_g": 1.0}

    def encoders(self) -> Dict[str, int]:
        ticks = int(self.x * 1000)
        return {"left": ticks, "right": ticks}

    def get_state(self) -> Dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
            "vx": self.vx,
            "omega": self.omega,
        }
