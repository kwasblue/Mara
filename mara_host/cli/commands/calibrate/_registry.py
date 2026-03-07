# mara_host/cli/commands/calibrate/_registry.py
"""Registry for calibrate commands."""

import argparse

from ._common import add_transport_args, show_calibrations
from .motor import cmd_motor
from .encoder import cmd_encoder
from .imu import cmd_imu
from .servo import cmd_servo
from .wheels import cmd_wheels
from .pid import cmd_pid


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register calibrate commands."""
    cal_parser = subparsers.add_parser(
        "calibrate",
        help="Calibration wizards",
        description="Calibrate motors, encoders, and sensors",
    )

    cal_sub = cal_parser.add_subparsers(
        dest="cal_cmd",
        title="calibration",
        metavar="<component>",
    )

    # motor
    motor_p = cal_sub.add_parser(
        "motor",
        help="Calibrate DC motor",
    )
    motor_p.add_argument("motor_id", type=int, nargs="?", default=0, help="Motor ID")
    add_transport_args(motor_p)
    motor_p.set_defaults(func=cmd_motor)

    # encoder
    encoder_p = cal_sub.add_parser(
        "encoder",
        help="Calibrate encoder",
    )
    encoder_p.add_argument("encoder_id", type=int, nargs="?", default=0, help="Encoder ID")
    add_transport_args(encoder_p)
    encoder_p.set_defaults(func=cmd_encoder)

    # imu
    imu_p = cal_sub.add_parser(
        "imu",
        help="Calibrate IMU",
    )
    add_transport_args(imu_p)
    imu_p.set_defaults(func=cmd_imu)

    # servo
    servo_p = cal_sub.add_parser(
        "servo",
        help="Calibrate servo range",
    )
    servo_p.add_argument("servo_id", type=int, nargs="?", default=0, help="Servo ID")
    add_transport_args(servo_p)
    servo_p.set_defaults(func=cmd_servo)

    # wheels
    wheels_p = cal_sub.add_parser(
        "wheels",
        help="Calibrate wheel diameter and base",
    )
    add_transport_args(wheels_p)
    wheels_p.set_defaults(func=cmd_wheels)

    # pid
    pid_p = cal_sub.add_parser(
        "pid",
        help="Test and tune PID controller",
    )
    pid_p.add_argument("motor_id", type=int, nargs="?", default=0, help="Motor ID")
    pid_p.add_argument("--kp", type=float, default=0.8, help="Proportional gain (default: 0.8)")
    pid_p.add_argument("--ki", type=float, default=0.1, help="Integral gain (default: 0.1)")
    pid_p.add_argument("--kd", type=float, default=0.05, help="Derivative gain (default: 0.05)")
    pid_p.add_argument("--sweep", action="store_true", help="Run parameter sweep")
    pid_p.add_argument("--targets", default="2.0,4.0,6.0,3.0,0.0",
                       help="Velocity targets (rad/s, comma-separated)")
    pid_p.add_argument("--hold", type=float, default=2.0,
                       help="Time to hold each target (seconds)")
    add_transport_args(pid_p)
    pid_p.set_defaults(func=cmd_pid)

    # Default
    cal_parser.set_defaults(func=lambda args: show_calibrations())
