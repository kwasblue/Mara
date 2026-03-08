# mara_host/workflows/calibration/servo.py
"""
Servo calibration workflow.

Helps find safe min/max angles for a servo.
"""

import asyncio
from typing import Optional

from mara_host.workflows.base import BaseWorkflow, WorkflowResult, WorkflowState


class ServoCalibrationWorkflow(BaseWorkflow):
    """
    Servo calibration workflow.

    Guides the user through finding safe minimum and maximum angles
    for a servo, with live testing.

    Usage:
        workflow = ServoCalibrationWorkflow(client)
        workflow.on_progress = lambda p, s: print(f"{p}%: {s}")

        result = await workflow.run(servo_id=0)
        if result.ok:
            print(f"Min: {result.data['min_angle']}")
            print(f"Max: {result.data['max_angle']}")
    """

    def __init__(self, client):
        super().__init__(client)
        self._user_response: Optional[str] = None
        self._user_response_event: Optional[asyncio.Event] = None
        self._current_angle = 90

    @property
    def name(self) -> str:
        return "Servo Calibration"

    async def run(
        self,
        servo_id: int = 0,
        initial_angle: int = 90,
        min_limit: int = 0,
        max_limit: int = 180,
    ) -> WorkflowResult:
        """
        Run servo calibration.

        Args:
            servo_id: Servo to calibrate (0-7)
            initial_angle: Starting angle (default center)
            min_limit: Absolute minimum angle limit
            max_limit: Absolute maximum angle limit

        Returns:
            WorkflowResult with min_angle, max_angle, center in data
        """
        self.reset()
        self._set_state(WorkflowState.RUNNING)
        self._current_angle = initial_angle

        min_angle: Optional[int] = None
        max_angle: Optional[int] = None

        try:
            self._emit_progress(0, "Starting servo calibration")

            # Move to center
            await self._set_servo_angle(servo_id, initial_angle)
            await asyncio.sleep(0.5)

            # Phase 1: Find minimum angle
            self._emit_progress(10, "Finding minimum angle")
            self._set_state(WorkflowState.WAITING_USER)

            # Request user to set minimum
            self.on_user_prompt(
                "Use the controls to move servo to minimum safe angle, then confirm",
                ["Set Minimum", "Cancel"]
            )

            response = await self._wait_for_response()
            if response is None or response == "Cancel":
                return WorkflowResult.cancelled()

            min_angle = self._current_angle
            self._set_state(WorkflowState.RUNNING)
            self._emit_progress(40, f"Minimum angle set: {min_angle}")

            # Phase 2: Find maximum angle
            self._emit_progress(50, "Finding maximum angle")
            self._set_state(WorkflowState.WAITING_USER)

            self.on_user_prompt(
                "Use the controls to move servo to maximum safe angle, then confirm",
                ["Set Maximum", "Cancel"]
            )

            response = await self._wait_for_response()
            if response is None or response == "Cancel":
                return WorkflowResult.cancelled()

            max_angle = self._current_angle
            self._set_state(WorkflowState.RUNNING)
            self._emit_progress(80, f"Maximum angle set: {max_angle}")

            # Ensure min < max
            if min_angle is not None and max_angle is not None:
                if min_angle > max_angle:
                    min_angle, max_angle = max_angle, min_angle

            # Calculate center
            center = (min_angle + max_angle) // 2

            # Move to center
            await self._set_servo_angle(servo_id, center)
            self._emit_progress(100, "Calibration complete")

            return WorkflowResult.success({
                "servo_id": servo_id,
                "min_angle": min_angle,
                "max_angle": max_angle,
                "center": center,
                "range": max_angle - min_angle,
            })

        except Exception as e:
            return WorkflowResult.failure(str(e))

    async def _set_servo_angle(self, servo_id: int, angle: int) -> None:
        """Set servo angle."""
        await self._send_command(
            "CMD_SERVO_SET_ANGLE",
            {"servo_id": servo_id, "angle": float(angle)},
        )

    def set_angle(self, angle: int) -> None:
        """
        Update current angle (called during interactive adjustment).

        Args:
            angle: New angle value
        """
        self._current_angle = angle

    async def _wait_for_response(self) -> Optional[str]:
        """Wait for user response."""
        self._user_response_event = asyncio.Event()
        self._user_response = None

        while not self._user_response_event.is_set():
            if self._check_cancelled():
                return None
            await asyncio.sleep(0.1)

        return self._user_response

    def respond(self, response: str) -> None:
        """Provide user response."""
        self._user_response = response
        if self._user_response_event:
            self._user_response_event.set()
