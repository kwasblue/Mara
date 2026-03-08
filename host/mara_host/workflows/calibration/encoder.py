# mara_host/workflows/calibration/encoder.py
"""
Encoder calibration workflow.

Determines ticks per revolution for encoder configuration.
"""

import asyncio
from typing import Optional

from mara_host.workflows.base import BaseWorkflow, WorkflowResult, WorkflowState


class EncoderCalibrationWorkflow(BaseWorkflow):
    """
    Encoder calibration workflow.

    Guides the user through finding ticks per revolution
    by manually rotating the wheel.

    Usage:
        workflow = EncoderCalibrationWorkflow(client)
        workflow.on_progress = lambda p, s: print(f"{p}%: {s}")

        result = await workflow.run(encoder_id=0)
        if result.ok:
            print(f"Ticks per revolution: {result.data['ticks_per_rev']}")
    """

    def __init__(self, client):
        super().__init__(client)
        self._user_response: Optional[str] = None
        self._user_response_event: Optional[asyncio.Event] = None
        self._current_count = 0

    @property
    def name(self) -> str:
        return "Encoder Calibration"

    async def run(
        self,
        encoder_id: int = 0,
        pin_a: int = 32,
        pin_b: int = 33,
    ) -> WorkflowResult:
        """
        Run encoder calibration.

        Args:
            encoder_id: Encoder to calibrate (0-3)
            pin_a: Encoder A pin
            pin_b: Encoder B pin

        Returns:
            WorkflowResult with ticks_per_rev in data
        """
        self.reset()
        self._set_state(WorkflowState.RUNNING)
        self._current_count = 0

        try:
            self._emit_progress(0, "Starting encoder calibration")

            # Attach encoder
            self._emit_progress(10, f"Attaching encoder {encoder_id}")
            await self._send_command(
                "CMD_ENCODER_ATTACH",
                {"encoder_id": encoder_id, "pin_a": pin_a, "pin_b": pin_b},
            )
            await asyncio.sleep(0.3)

            # Reset count
            self._emit_progress(20, "Resetting counter")
            await self._send_command(
                "CMD_ENCODER_RESET",
                {"encoder_id": encoder_id},
            )
            self._current_count = 0

            # Wait for user to mark start position
            self._emit_progress(30, "Mark starting position")
            self._set_state(WorkflowState.WAITING_USER)

            self.on_user_prompt(
                "Mark the current wheel position, then click Continue",
                ["Continue", "Cancel"]
            )

            response = await self._wait_for_response()
            if response is None or response == "Cancel":
                return WorkflowResult.cancelled()

            self._set_state(WorkflowState.RUNNING)

            # Wait for user to complete one revolution
            self._emit_progress(50, "Rotate wheel one revolution")
            self._set_state(WorkflowState.WAITING_USER)

            self.on_user_prompt(
                "Rotate the wheel exactly ONE complete revolution, then click Done",
                ["Done", "Cancel"]
            )

            response = await self._wait_for_response()
            if response is None or response == "Cancel":
                return WorkflowResult.cancelled()

            self._set_state(WorkflowState.RUNNING)

            # Get final count
            ticks_per_rev = abs(self._current_count)

            self._emit_progress(100, f"Calibration complete: {ticks_per_rev} ticks/rev")

            return WorkflowResult.success({
                "encoder_id": encoder_id,
                "ticks_per_revolution": ticks_per_rev,
                "pin_a": pin_a,
                "pin_b": pin_b,
            })

        except Exception as e:
            return WorkflowResult.failure(str(e))

    def update_count(self, count: int) -> None:
        """
        Update current encoder count (called from telemetry).

        Args:
            count: Current encoder count
        """
        self._current_count = count

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
