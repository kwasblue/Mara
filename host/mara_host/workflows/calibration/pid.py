# mara_host/workflows/calibration/pid.py
"""
PID tuning workflow.

Provides automated and manual PID tuning methods.
"""

import asyncio
from dataclasses import dataclass
from statistics import mean

from mara_host.workflows.base import BaseWorkflow, WorkflowResult, WorkflowState


@dataclass
class PIDGains:
    """PID controller gains."""
    kp: float
    ki: float
    kd: float


@dataclass
class StepResponse:
    """Step response metrics."""
    rise_time: float  # Time to reach 90% of target
    overshoot: float  # Percentage overshoot
    settling_time: float  # Time to stay within 2% of target
    steady_state_error: float  # Final error


class PIDTuningWorkflow(BaseWorkflow):
    """
    PID tuning workflow.

    Provides methods for tuning motor velocity PID:
    - Manual: Apply gains and observe response
    - Step test: Measure response to step input
    - Auto-tune: Ziegler-Nichols style tuning (future)

    Usage:
        workflow = PIDTuningWorkflow(client)
        workflow.on_progress = lambda p, s: print(f"{p}%: {s}")

        # Manual tuning with step test
        result = await workflow.run(
            motor_id=0,
            kp=1.0, ki=0.0, kd=0.0,
            target_velocity=10.0,
            test_duration=3.0,
        )

        if result.ok:
            print(f"Overshoot: {result.data['overshoot']}%")
            print(f"Settling time: {result.data['settling_time']}s")
    """

    def __init__(self, client):
        super().__init__(client)
        self._velocity_samples: list[tuple[float, float]] = []  # (time, velocity)
        self._collecting = False
        self._start_time = 0.0

    @property
    def name(self) -> str:
        return "PID Tuning"

    async def run(
        self,
        motor_id: int = 0,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        target_velocity: float = 10.0,
        test_duration: float = 3.0,
    ) -> WorkflowResult:
        """
        Run PID tuning step test.

        Args:
            motor_id: Motor to tune (0-3)
            kp, ki, kd: PID gains to test
            target_velocity: Target velocity in rad/s
            test_duration: Test duration in seconds

        Returns:
            WorkflowResult with step response metrics
        """
        self.reset()
        self._set_state(WorkflowState.RUNNING)
        self._velocity_samples = []
        self._collecting = False

        try:
            self._emit_progress(0, "Applying PID gains")

            # Apply gains
            await self._send_command(
                "CMD_DC_SET_VEL_GAINS",
                {"motor_id": motor_id, "kp": kp, "ki": ki, "kd": kd},
            )
            await asyncio.sleep(0.1)

            # Enable PID
            await self._send_command(
                "CMD_DC_VEL_PID_ENABLE",
                {"motor_id": motor_id, "enable": True},
            )
            await asyncio.sleep(0.1)

            self._emit_progress(10, "Starting step test")

            # Start collecting samples
            self._collecting = True
            self._start_time = asyncio.get_event_loop().time()

            # Apply step input
            await self._send_command(
                "CMD_DC_SET_VEL_TARGET",
                {"motor_id": motor_id, "omega": target_velocity},
            )

            # Collect data
            elapsed = 0.0
            while elapsed < test_duration:
                if self._check_cancelled():
                    await self._stop_motor(motor_id)
                    return WorkflowResult.cancelled()

                progress = 10 + int((elapsed / test_duration) * 70)
                self._emit_progress(progress, f"Testing... {elapsed:.1f}s")

                await asyncio.sleep(0.05)
                elapsed = asyncio.get_event_loop().time() - self._start_time

            self._collecting = False

            # Stop motor
            self._emit_progress(85, "Stopping motor")
            await self._send_command(
                "CMD_DC_SET_VEL_TARGET",
                {"motor_id": motor_id, "omega": 0.0},
            )
            await asyncio.sleep(0.5)

            await self._send_command(
                "CMD_DC_VEL_PID_ENABLE",
                {"motor_id": motor_id, "enable": False},
            )

            # Analyze response
            self._emit_progress(90, "Analyzing response")

            metrics = self._analyze_response(target_velocity)

            self._emit_progress(100, "Test complete")

            return WorkflowResult.success({
                "motor_id": motor_id,
                "gains": {"kp": kp, "ki": ki, "kd": kd},
                "target": target_velocity,
                "rise_time": metrics.rise_time,
                "overshoot": metrics.overshoot,
                "settling_time": metrics.settling_time,
                "steady_state_error": metrics.steady_state_error,
                "num_samples": len(self._velocity_samples),
            })

        except Exception as e:
            await self._stop_motor(motor_id)
            return WorkflowResult.failure(str(e))
        finally:
            self._collecting = False

    async def _stop_motor(self, motor_id: int) -> None:
        """Stop motor and disable PID."""
        await self._send_command(
            "CMD_DC_SET_VEL_TARGET",
            {"motor_id": motor_id, "omega": 0.0},
        )
        await self._send_command(
            "CMD_DC_VEL_PID_ENABLE",
            {"motor_id": motor_id, "enable": False},
        )

    def add_velocity_sample(self, velocity: float) -> None:
        """
        Add velocity sample (called from telemetry).

        Args:
            velocity: Current motor velocity in rad/s
        """
        if self._collecting:
            t = asyncio.get_event_loop().time() - self._start_time
            self._velocity_samples.append((t, velocity))

    def _analyze_response(self, target: float) -> StepResponse:
        """
        Analyze step response data.

        Args:
            target: Target velocity

        Returns:
            StepResponse metrics
        """
        if len(self._velocity_samples) < 10:
            return StepResponse(
                rise_time=0.0,
                overshoot=0.0,
                settling_time=0.0,
                steady_state_error=0.0,
            )

        times, velocities = zip(*self._velocity_samples)

        # Rise time: time to reach 90% of target
        rise_threshold = 0.9 * target
        rise_time = 0.0
        for t, v in self._velocity_samples:
            if abs(v) >= abs(rise_threshold):
                rise_time = t
                break

        # Overshoot: max deviation above target
        max_velocity = max(abs(v) for v in velocities)
        overshoot = 0.0
        if abs(target) > 0:
            overshoot = max(0, (max_velocity - abs(target)) / abs(target) * 100)

        # Settling time: time to stay within 2% of target
        settling_band = 0.02 * abs(target) if abs(target) > 0 else 0.1
        settling_time = times[-1]
        for t, v in reversed(self._velocity_samples):
            if abs(v - target) > settling_band:
                settling_time = t
                break

        # Steady state error: average of last 10 samples
        last_velocities = [v for _, v in self._velocity_samples[-10:]]
        steady_state = mean(last_velocities) if last_velocities else 0.0
        steady_state_error = abs(target - steady_state)

        return StepResponse(
            rise_time=rise_time,
            overshoot=overshoot,
            settling_time=settling_time,
            steady_state_error=steady_state_error,
        )
