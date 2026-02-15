# robot_host/modules/arm_ik.py

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, acos, cos, sin, degrees
from typing import Any, Dict, List, Literal, Optional

from robot_host.telemetry.host_module import TelemetryHostModule # your base
from robot_host.core.event_bus import EventBus          # for type hints
from robot_host.command.client import AsyncRobotClient         # for type hints


JointType = Literal["servo", "stepper"]


@dataclass
class JointConfig:
    name: str
    type: JointType
    channel: int
    min_deg: float
    max_deg: float
    home_deg: float
    steps_per_rev: Optional[int] = None   # for stepper
    microsteps: Optional[int] = None      # for stepper


@dataclass
class LinkConfig:
    length_m: float


@dataclass
class ArmSettings:
    joints: List[JointConfig]
    links: List[LinkConfig]
    move_speed_deg_s: float = 45.0


class ArmKinematics:
    """
    Simple planar arm model:

      joint 0: base yaw
      joint 1: shoulder
      joint 2: elbow

    Links:
      L1: shoulder -> elbow
      L2: elbow -> wrist (end-effector)
    """

    def __init__(self, cfg: ArmSettings):
        if len(cfg.joints) < 3:
            raise ValueError("ArmKinematics expects at least 3 joints (base, shoulder, elbow)")
        if len(cfg.links) != 2:
            raise ValueError("This simple model expects exactly 2 links")

        self.cfg = cfg
        self.base_joint = cfg.joints[0]
        self.shoulder_joint = cfg.joints[1]
        self.elbow_joint = cfg.joints[2]
        self.L1 = cfg.links[0].length_m
        self.L2 = cfg.links[1].length_m

    @staticmethod
    def _clamp(joint: JointConfig, angle_deg: float) -> float:
        return max(joint.min_deg, min(joint.max_deg, angle_deg))

    def ik_planar(
        self,
        x: float,
        y: float,
        elbow_up: bool = True,
    ) -> Dict[str, float]:
        """
        Given planar (x, y) in meters, compute base/shoulder/elbow joint angles in deg.
        Returns a dict keyed by joint name.
        """
        # distance to target in XY plane
        r = (x ** 2 + y ** 2) ** 0.5

        # clamp to reachable workspace for basic robustness
        max_r = self.L1 + self.L2
        if r > max_r:
            r = max_r - 1e-6

        # law of cosines for elbow
        cos_elbow = (r ** 2 - self.L1 ** 2 - self.L2 ** 2) / (2 * self.L1 * self.L2)
        cos_elbow = max(-1.0, min(1.0, cos_elbow))

        theta2 = acos(cos_elbow)        # elbow angle in radians
        if not elbow_up:
            theta2 = -theta2

        # shoulder via “two-link” geometry
        k1 = self.L1 + self.L2 * cos(theta2)
        k2 = self.L2 * sin(theta2)
        theta1 = atan2(y, x) - atan2(k2, k1)

        base_deg = degrees(atan2(y, x))
        shoulder_deg = degrees(theta1)
        elbow_deg = degrees(theta2)

        base_deg = self._clamp(self.base_joint, base_deg)
        shoulder_deg = self._clamp(self.shoulder_joint, shoulder_deg)
        elbow_deg = self._clamp(self.elbow_joint, elbow_deg)

        return {
            self.base_joint.name: base_deg,
            self.shoulder_joint.name: shoulder_deg,
            self.elbow_joint.name: elbow_deg,
        }


class ArmIKModule(TelemetryHostModule):
    """
    Host-side arm controller:

    - Listens for high-level events:
        * ARM_HOME
        * ARM_MOVE_JOINTS
        * ARM_MOVE_CARTESIAN
    - Runs IK for Cartesian motions
    - Sends ONLY low-level MCU commands like:
        * SERVO_MOVE
        * STEPPER_MOVE_ABS

    It does NOT introduce any new MCU commands.
    """

    def __init__(self, bus: EventBus, client: AsyncRobotClient, settings: Dict[str, Any]):
        super().__init__(bus, client, settings)

        joints_raw = settings.get("joints", [])
        links_raw = settings.get("links", [])
        if len(joints_raw) < 3:
            raise ValueError("ArmIKModule requires at least 3 joints (base, shoulder, elbow)")
        if len(links_raw) != 2:
            raise ValueError("ArmIKModule requires exactly 2 links")

        joint_cfgs = [JointConfig(**j) for j in joints_raw]
        link_cfgs = [LinkConfig(**l) for l in links_raw]

        self.arm_cfg = ArmSettings(
            joints=joint_cfgs,
            links=link_cfgs,
            move_speed_deg_s=settings.get("move_speed_deg_s", 45.0),
        )
        self.kin = ArmKinematics(self.arm_cfg)

        # convenience mapping
        self._joints_by_name = {j.name: j for j in joint_cfgs}

    # ------------------------------------------------------------------ #
    # HostModule interface
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        # subscribe to high-level host events
        self.bus.subscribe("ARM_HOME", self.on_home)
        self.bus.subscribe("ARM_MOVE_JOINTS", self.on_move_joints)
        self.bus.subscribe("ARM_MOVE_CARTESIAN", self.on_move_cartesian)

        # optional: automatically home on startup
        if self.settings.get("home_on_start", False):
            self._home()

    def stop(self) -> None:
        # nothing to clean up right now; unsubscribing optional
        pass

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #
    def on_home(self, event) -> None:
        self._home()

    def on_move_joints(self, event) -> None:
        """
        Expect data like:
          {"base": 0.0, "shoulder": 45.0, "elbow": 30.0}
        """
        data = event.data or {}
        for joint_name, target_deg in data.items():
            joint = self._joints_by_name.get(joint_name)
            if not joint:
                continue
            self._move_joint_deg(joint, float(target_deg))

    def on_move_cartesian(self, event) -> None:
        """
        Expect data like:
          {"x": 0.12, "y": 0.05, "elbow_up": true}
        """
        data = event.data or {}
        x = float(data["x"])
        y = float(data["y"])
        elbow_up = bool(data.get("elbow_up", True))

        target_angles = self.kin.ik_planar(x, y, elbow_up=elbow_up)

        # Reuse joint motion helper
        for joint_name, angle_deg in target_angles.items():
            joint = self._joints_by_name.get(joint_name)
            if not joint:
                continue
            self._move_joint_deg(joint, angle_deg)

    # ------------------------------------------------------------------ #
    # Helpers: high-level behaviors
    # ------------------------------------------------------------------ #
    def _home(self) -> None:
        for joint in self.arm_cfg.joints:
            self._move_joint_deg(joint, joint.home_deg)

    # ------------------------------------------------------------------ #
    # Helpers: low-level commands to MCU
    # ------------------------------------------------------------------ #
    def _move_joint_deg(self, joint: JointConfig, angle_deg: float) -> None:
        # clamp to limits again for safety
        angle_deg = max(joint.min_deg, min(joint.max_deg, angle_deg))

        if joint.type == "servo":
            self._send_servo_move(joint.channel, angle_deg)
        elif joint.type == "stepper":
            self._send_stepper_move_abs(joint, angle_deg)

    def _send_servo_move(self, channel: int, angle_deg: float) -> None:
        """
        LOW-LEVEL: this is where we talk the MCU command vocabulary.
        No arm-specific commands. Just SERVO_MOVE.
        """
        self.client.send_command("SERVO_MOVE", {
            "channel": channel,
            "angle_deg": angle_deg,
        })

    def _send_stepper_move_abs(self, joint: JointConfig, angle_deg: float) -> None:
        steps_per_rev = joint.steps_per_rev or 200
        microsteps = joint.microsteps or 16
        steps_per_deg = (steps_per_rev * microsteps) / 360.0
        target_steps = int(round(angle_deg * steps_per_deg))

        self.client.send_command("STEPPER_MOVE_ABS", {
            "channel": joint.channel,
            "target_steps": target_steps,
            # you can add max_rate, accel, etc. later if your MCU supports it
        })
