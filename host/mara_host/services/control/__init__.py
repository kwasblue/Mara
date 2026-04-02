# mara_host/services/control/__init__.py
"""
Control services for robot state, motion, and hardware management.

Provides high-level control operations that can be shared
between GUI and CLI interfaces.

Example:
    from mara_host.services.control import StateService, MotionService
    from mara_host.services.control import MotorService, ServoService, GpioService

    state_svc = StateService(client)
    result = await state_svc.arm()
    if result.ok:
        print(f"Robot armed: {result.state}")

    motor_svc = MotorService(client)
    await motor_svc.set_speed(0, 0.5)
"""

from mara_host.services.control.service_base import ConfigurableService
from mara_host.services.control.state_service import (
    StateService,
    RobotState,
)
from mara_host.services.control.motion_service import (
    MotionService,
    Velocity,
)
from mara_host.services.control.motor_service import (
    MotorService,
    MotorConfig,
    MotorState,
)
from mara_host.services.control.servo_service import (
    ServoService,
    ServoConfig,
    ServoState,
)
from mara_host.services.control.composite_service import (
    CompositeService,
)
from mara_host.services.control.gpio_service import (
    GpioService,
    GpioChannel,
    GpioMode,
)
from mara_host.services.control.stepper_service import (
    StepperService,
    StepperConfig,
    StepperState,
)
from mara_host.services.control.encoder_service import (
    EncoderService,
    EncoderConfig,
    EncoderState,
)
from mara_host.services.control.imu_service import (
    ImuService,
    ImuReading,
    ImuBias,
)
from mara_host.services.control.ultrasonic_service import (
    UltrasonicService,
    UltrasonicConfig,
    UltrasonicState,
)
from mara_host.services.control.pwm_service import (
    PwmService,
    PwmConfig,
    PwmState,
)
from mara_host.services.control.wifi_service import (
    WifiService,
)
from mara_host.services.control.controller_service import (
    ControllerService,
    ControllerSlot,
    ControllerType,
    ObserverSlot,
    ObserverType,
)
from mara_host.services.control.signal_service import (
    SignalService,
    Signal,
    SignalKind,
)
from mara_host.services.control.control_graph_service import (
    ControlGraphService,
)
from mara_host.services.control.pid_service import (
    PidService,
    PidGains,
    PidState,
)
from mara_host.core.result import (
    ServiceResult,
    send_command,
)

__all__ = [
    # Base class
    "ConfigurableService",
    # State management
    "StateService",
    "RobotState",
    # Motion control
    "MotionService",
    "Velocity",
    # Motor control
    "MotorService",
    "MotorConfig",
    "MotorState",
    # Servo control
    "ServoService",
    "ServoConfig",
    "ServoState",
    # Composite/batch control
    "CompositeService",
    # GPIO control
    "GpioService",
    "GpioChannel",
    "GpioMode",
    # Stepper control
    "StepperService",
    "StepperConfig",
    "StepperState",
    # Encoder control
    "EncoderService",
    "EncoderConfig",
    "EncoderState",
    # IMU control
    "ImuService",
    "ImuReading",
    "ImuBias",
    # Ultrasonic control
    "UltrasonicService",
    "UltrasonicConfig",
    "UltrasonicState",
    # PWM control
    "PwmService",
    "PwmConfig",
    "PwmState",
    # Wi-Fi control
    "WifiService",
    # Control graph
    "ControlGraphService",
    # Signal bus service
    "SignalService",
    "Signal",
    "SignalKind",
    # Controller/Observer system
    "ControllerService",
    "ControllerSlot",
    "ControllerType",
    "ObserverSlot",
    "ObserverType",
    # PID control
    "PidService",
    "PidGains",
    "PidState",
    # Result type
    "ServiceResult",
    # Helpers
    "send_command",
]
