# mara_host/workflows/calibration/motor.py
"""
Motor calibration workflow.

Finds motor dead zone and direction through automated testing.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional

from mara_host.workflows.base import BaseWorkflow, WorkflowResult, WorkflowState


@dataclass
class MotorCalibrationParams:
    """Parameters for motor calibration."""
    motor_id: int = 0
    start_pwm: int = 5
    end_pwm: int = 100
    step_pwm: int = 5
    step_delay_s: float = 0.5


class MotorCalibrationWorkflow(BaseWorkflow):
    """
    Motor calibration workflow.

    Determines the motor's dead zone (minimum PWM to start moving)
    and verifies direction.

    Usage:
        workflow = MotorCalibrationWorkflow(client)
        workflow.on_progress = lambda p, s: print(f"{p}%: {s}")

        result = await workflow.run(motor_id=0)
        if result.ok:
            print(f"Dead zone: {result.data['dead_zone']}%")
            print(f"Inverted: {result.data['inverted']}")
    """

    def __init__(self, client):
        super().__init__(client)
        self._user_response: Optional[str] = None
        self._user_response_event: Optional[asyncio.Event] = None

    @property
    def name(self) -> str:
        return "Motor Calibration"

    async def run(
        self,
        motor_id: int = 0,
        start_pwm: int = 5,
        end_pwm: int = 100,
        step_pwm: int = 5,
        step_delay_s: float = 0.5,
    ) -> WorkflowResult:
        """
        Run motor calibration.

        Args:
            motor_id: Motor to calibrate (0-3)
            start_pwm: Starting PWM percentage
            end_pwm: Maximum PWM percentage to test
            step_pwm: PWM increment per step
            step_delay_s: Delay between steps in seconds

        Returns:
            WorkflowResult with dead_zone and inverted in data
        """
        self.reset()
        self._set_state(WorkflowState.RUNNING)

        dead_zone = 0.0
        inverted = False

        try:
            # Phase 1: Find dead zone using binary search
            self._emit_progress(0, "Starting dead zone search")

            search_min = start_pwm
            search_max = end_pwm

            while search_max - search_min > step_pwm:
                if self._check_cancelled():
                    await self._stop_motor(motor_id)
                    return WorkflowResult.cancelled()

                # Test midpoint
                test_pwm = (search_min + search_max) // 2
                progress = int((100 - (search_max - search_min)) / 100 * 60)
                self._emit_progress(progress, f"Testing {test_pwm}% PWM")

                await self._set_motor_speed(motor_id, test_pwm / 100.0)
                await asyncio.sleep(step_delay_s)

                # Wait for user response
                self._set_state(WorkflowState.WAITING_USER)
                is_moving = await self._wait_for_user_confirmation(
                    f"Is the motor moving at {test_pwm}% PWM?"
                )

                if is_moving is None:  # Cancelled
                    await self._stop_motor(motor_id)
                    return WorkflowResult.cancelled()

                self._set_state(WorkflowState.RUNNING)

                if is_moving:
                    search_max = test_pwm
                else:
                    search_min = test_pwm

            dead_zone = search_max / 100.0
            await self._stop_motor(motor_id)
            self._emit_progress(60, f"Dead zone found: {search_max}%")

            # Phase 2: Direction check
            if self._check_cancelled():
                return WorkflowResult.cancelled()

            self._emit_progress(70, "Testing direction")
            await self._set_motor_speed(motor_id, 0.3)
            await asyncio.sleep(1.0)
            await self._stop_motor(motor_id)

            self._set_state(WorkflowState.WAITING_USER)
            correct_direction = await self._wait_for_user_confirmation(
                "Did the motor spin in the expected (forward) direction?"
            )

            if correct_direction is None:
                return WorkflowResult.cancelled()

            inverted = not correct_direction
            self._set_state(WorkflowState.RUNNING)

            # Phase 3: Max speed test (optional)
            self._emit_progress(90, "Calibration complete")

            return WorkflowResult.success({
                "motor_id": motor_id,
                "dead_zone": dead_zone,
                "dead_zone_percent": int(dead_zone * 100),
                "inverted": inverted,
            })

        except Exception as e:
            await self._stop_motor(motor_id)
            return WorkflowResult.failure(str(e))

    async def _set_motor_speed(self, motor_id: int, speed: float) -> None:
        """Set motor speed (0.0-1.0)."""
        await self._send_command(
            "CMD_DC_MOTOR_SET_SPEED",
            {"motor_id": motor_id, "speed": speed},
        )

    async def _stop_motor(self, motor_id: int) -> None:
        """Stop the motor."""
        await self._set_motor_speed(motor_id, 0.0)

    async def _wait_for_user_confirmation(self, question: str) -> Optional[bool]:
        """
        Wait for user to confirm yes/no.

        Args:
            question: Question to ask user

        Returns:
            True for yes, False for no, None if cancelled
        """
        self._user_response_event = asyncio.Event()
        self._user_response = None

        # Notify consumer to show prompt
        self.on_user_prompt(question, ["Yes", "No"])

        # Wait for response
        while not self._user_response_event.is_set():
            if self._check_cancelled():
                return None
            await asyncio.sleep(0.1)

        return self._user_response == "Yes"

    def respond(self, response: str) -> None:
        """
        Provide user response to a prompt.

        Called by the consumer (GUI/CLI) when user responds.

        Args:
            response: User's response ("Yes", "No", etc.)
        """
        self._user_response = response
        if self._user_response_event:
            self._user_response_event.set()
