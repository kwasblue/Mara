from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# Match your existing firmware command names
CMD_CLEAR_ESTOP         = "CMD_CLEAR_ESTOP"
CMD_SET_MODE            = "CMD_SET_MODE"
CMD_TELEM_SET_INTERVAL  = "CMD_TELEM_SET_INTERVAL"
CMD_STEPPER_ENABLE      = "CMD_STEPPER_ENABLE"
CMD_STEPPER_MOVE_REL    = "CMD_STEPPER_MOVE_REL"
CMD_STEPPER_STOP        = "CMD_STEPPER_STOP"


@dataclass
class PillCarouselConfig:
    motor_id: int = 0              # stepper motor_id on MCU
    steps_per_rev: int = 200       # same meaning as your current runner
    slots_per_rev: int = 12        # how many pill slots
    default_speed_rps: float = 0.5 # rev/s (host converts to steps/s)
    cover_offset_steps: int = 20


class PillCarousel:
    """
    Host-side pill carousel controller built on your existing stepper commands.

    - Uses CMD_STEPPER_ENABLE, CMD_STEPPER_MOVE_REL, CMD_STEPPER_STOP.
    - Movements are relative.
    - No homing yet: you manually align a slot and call set_current_slot(0).
    """

    def __init__(self, client, config: Optional[PillCarouselConfig] = None):
        self.client = client
        self.config = config or PillCarouselConfig()

        self.steps_per_slot: float = self.config.steps_per_rev / self.config.slots_per_rev
        self.current_slot: int = 0
        self.enabled: bool = False
        
        # 200 / 5 = 40 center-to-center
        self.steps_per_slot: float = self.config.steps_per_rev / self.config.slots_per_rev

        self.current_slot: int = 0
        self.enabled: bool = False


    # ------------------------------------------------------------------ #
    # Robot / safety helpers
    # ------------------------------------------------------------------ #

    async def init_robot(self, telem_interval_ms: int = 500) -> None:
        """
        Mirrors your stepper runner startup:
        - optional telemetry config
        - clear ESTOP
        - set mode ARMED/ACTIVE
        - enable stepper
        """
        # telemetry (best-effort)
        try:
            await self.client.send_json_cmd(
                CMD_TELEM_SET_INTERVAL,
                {"interval_ms": telem_interval_ms},
            )
        except Exception:
            pass

        await self.client.send_json_cmd(CMD_CLEAR_ESTOP, {})
        await self.client.send_json_cmd(CMD_SET_MODE, {"mode": "ARMED"})
        await self.client.send_json_cmd(CMD_SET_MODE, {"mode": "ACTIVE"})

        await self.enable_stepper(True)

    async def shutdown_robot(self) -> None:
        """
        Stop and disable stepper.
        """
        try:
            await self.client.send_json_cmd(
                CMD_STEPPER_STOP, {"motor_id": self.config.motor_id}
            )
        except Exception:
            pass

        await self.enable_stepper(False)

    # ------------------------------------------------------------------ #
    # Low-level stepper helpers
    # ------------------------------------------------------------------ #

    async def enable_stepper(self, enable: bool = True) -> None:
        await self.client.send_json_cmd(
            CMD_STEPPER_ENABLE,
            {"motor_id": self.config.motor_id, "enable": enable},
        )
        self.enabled = enable

    async def _move_steps(
        self,
        steps: int,
        speed_rps: Optional[float] = None,
    ) -> None:
        """
        Relative move: positive = forward, negative = backward.
        Uses CMD_STEPPER_MOVE_REL with speed_steps_s like your runner.
        """
        if steps == 0:
            return

        if not self.enabled:
            await self.enable_stepper(True)

        speed_rps = speed_rps if speed_rps is not None else self.config.default_speed_rps
        speed_steps_s = speed_rps * self.config.steps_per_rev

        await self.client.send_json_cmd(
            CMD_STEPPER_MOVE_REL,
            {
                "motor_id": self.config.motor_id,
                "steps": int(steps),
                "speed_steps_s": float(speed_steps_s),
            },
        )

    # ------------------------------------------------------------------ #
    # Slot-level API
    # ------------------------------------------------------------------ #

    def set_current_slot(self, slot_index: int) -> None:
        """
        Tell the controller which slot is currently aligned.

        At boot: manually rotate the disc so 'slot 0' is over the chute,
        then call set_current_slot(0).
        """
        self.current_slot = slot_index % self.config.slots_per_rev

    async def goto_slot(
        self,
        target_slot: int,
        speed_rps: Optional[float] = None,
    ) -> None:
        """
        Move from current_slot to target_slot, forward only (wrap-around).
        """
        target_slot = target_slot % self.config.slots_per_rev
        delta_slots = (target_slot - self.current_slot) % self.config.slots_per_rev
        steps = int(round(delta_slots * self.steps_per_slot))

        print(
            f"[PILL] Goto slot {target_slot} "
            f"(from {self.current_slot}, delta_slots={delta_slots}, steps={steps})"
        )

        await self._move_steps(steps, speed_rps)
        self.current_slot = target_slot

    async def step_to_next_slot(self, speed_rps: Optional[float] = None) -> None:
        """
        Convenience: move exactly one slot forward.
        """
        next_slot = (self.current_slot + 1) % self.config.slots_per_rev
        await self.goto_slot(next_slot, speed_rps)

    async def spin_full_rev(self, speed_rps: Optional[float] = None) -> None:
        """
        Rotate one full revolution (for mechanical testing).
        """
        speed_rps = speed_rps if speed_rps is not None else self.config.default_speed_rps
        steps = self.config.steps_per_rev

        print(f"[PILL] Spinning full revolution ({steps} steps, {speed_rps} rps)")
        await self._move_steps(steps, speed_rps)
    
        
    async def cover_current_slot(self, speed_rps: Optional[float] = None) -> None:
        """
        Nudge forward by cover_offset_steps to fully cover the current slot
        with the chute / opening.
        """
        steps = self.config.cover_offset_steps
        print(f"[PILL] Covering current slot {self.current_slot} (+{steps} steps)")
        await self._move_steps(steps, speed_rps)

    async def uncover_current_slot(self, speed_rps: Optional[float] = None) -> None:
        """
        Nudge backward by cover_offset_steps to return to the neutral position
        for this slot (e.g., between slots or wherever you prefer).
        """
        steps = -self.config.cover_offset_steps
        print(f"[PILL] Uncovering current slot {self.current_slot} ({steps} steps)")
        await self._move_steps(steps, speed_rps)

