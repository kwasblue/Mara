# mara_host/runtime/robot_runtime.py
"""
Base robot runtime wiring - orchestrates all host modules.

This module belongs in runtime/ because it orchestrates domain modules
(motor, sensor, telemetry) rather than providing core infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.event_bus import EventBus
from ..command.client import MaraClient
from ..core.settings import HostSettings

from ..transport.tcp_transport import AsyncTcpTransport
from ..transport.serial_transport import SerialTransport
from ..transport.bluetooth_transport import BluetoothSerialTransport

from ..telemetry.host_module import TelemetryHostModule
from ..sensor.encoder import EncoderHostModule, EncoderDefaults
from ..motor.motion import MotionHostModule
from ..module.modes import ModeHostModule
from ..module.telemetry_ctl import TelemetryControlModule
from ..module.logging_ctl import LoggingControlModule


@dataclass
class BaseRobotRuntime:
    """
    Base runtime wiring for any robot using this MCU host.

    This is the generic “platform”:
      - One EventBus shared by everything.
      - One MaraClient (transport + protocol).
      - Common host modules (telemetry, motion, modes, etc.) as optional fields.

    Robot-specific runtimes/classes should compose this, not replace it.
    """
    bus: EventBus
    client: MaraClient

    telemetry: TelemetryHostModule | None = None
    encoder: EncoderHostModule | None = None
    motion: MotionHostModule | None = None
    modes: ModeHostModule | None = None
    telemetry_ctl: TelemetryControlModule | None = None
    logging_ctl: LoggingControlModule | None = None


async def build_base_runtime(profile: str = "default") -> BaseRobotRuntime:
    """
    Build the base runtime for a given host profile.

    This:
      - Loads HostSettings for the profile.
      - Creates EventBus.
      - Selects and constructs the transport (TCP / serial / BLE).
      - Builds and starts MaraClient on that transport.
      - Wires in common host modules based on feature flags.
    """
    settings = HostSettings.load(profile)
    bus = EventBus()

    # --- Transport selection ---
    t_cfg = settings.transport
    if t_cfg.type == "tcp":
        transport = AsyncTcpTransport(host=t_cfg.host, port=t_cfg.port)
    elif t_cfg.type == "serial":
        transport = SerialTransport(
            port=t_cfg.serial_port,
            baudrate=t_cfg.baudrate,
        )
    elif t_cfg.type == "ble":
        transport = BluetoothSerialTransport.auto(
            device_name=t_cfg.ble_name,
            baudrate=t_cfg.baudrate,
        )
    else:
        raise ValueError(f"Unknown transport type: {t_cfg.type}")

    # --- Core client ---
    client = MaraClient(transport, bus=bus)
    await client.start()

    # --- Host-side modules ---

    telemetry = TelemetryHostModule(bus) if settings.features.telemetry else None

    encoder = (
        EncoderHostModule(
            bus,
            client,
            EncoderDefaults(
                encoder_id=settings.encoder_defaults.encoder_id,
                pin_a=settings.encoder_defaults.pin_a,
                pin_b=settings.encoder_defaults.pin_b,
            ),
        )
        if settings.features.encoder
        else None
    )

    motion = (
        MotionHostModule(bus, client)
        if settings.features.motion
        else None
    )

    modes = (
        ModeHostModule(bus, client)
        if settings.features.modes
        else None
    )

    telemetry_ctl = TelemetryControlModule(bus, client)
    logging_ctl = LoggingControlModule(bus, client)

    return BaseRobotRuntime(
        bus=bus,
        client=client,
        telemetry=telemetry,
        encoder=encoder,
        motion=motion,
        modes=modes,
        telemetry_ctl=telemetry_ctl,
        logging_ctl=logging_ctl,
    )


# Optional: keep old name for backwards compatibility
async def build_runtime(profile: str = "default") -> BaseRobotRuntime:
    """Backward-compatible alias for build_base_runtime()."""
    return await build_base_runtime(profile)
