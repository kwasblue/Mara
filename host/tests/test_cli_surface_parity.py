import argparse
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from mara_host.core.result import Result


class FakeCLIContext:
    def __init__(self):
        self.gpio_service = SimpleNamespace(
            write=AsyncMock(return_value=Result.success({"channel": 0, "value": 1})),
            read=AsyncMock(return_value=Result.success({"channel": 0, "value": 1})),
        )
        self.servo_service = SimpleNamespace(
            attach=AsyncMock(return_value=Result.success({"servo_id": 0, "channel": 18})),
            set_angle=AsyncMock(return_value=Result.success({"servo_id": 0, "angle": 90})),
        )
        self.encoder_service = SimpleNamespace(
            attach=AsyncMock(return_value=Result.success({"encoder_id": 0})),
            detach=AsyncMock(return_value=Result.success({"encoder_id": 0})),
            read=AsyncMock(return_value=Result.success({"encoder_id": 0, "ticks": 123})),
            reset=AsyncMock(return_value=Result.success({"encoder_id": 0})),
        )
        self.imu_service = SimpleNamespace(
            read=AsyncMock(return_value=Result.success({"imu": True})),
            calibrate=AsyncMock(return_value=Result.success({"started": True})),
            set_bias=AsyncMock(return_value=Result.success({"bias": True})),
        )
        self.ultrasonic_service = SimpleNamespace(
            attach=AsyncMock(return_value=Result.success({"sensor_id": 0})),
            detach=AsyncMock(return_value=Result.success({"sensor_id": 0})),
            read=AsyncMock(return_value=Result.success({"sensor_id": 0, "distance_cm": 42.0})),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _patch_ctx(monkeypatch, fake_ctx):
    from mara_host.cli import context as cli_context
    monkeypatch.setattr(cli_context.CLIContext, "from_args", staticmethod(lambda args: fake_ctx))


def test_cli_gpio_write_uses_gpio_service(monkeypatch):
    from mara_host.cli.commands.gpio import cmd_gpio_write

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(channel=7, value=1, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_gpio_write(args)

    assert rc == 0
    fake_ctx.gpio_service.write.assert_awaited_once_with(7, 1)


def test_cli_gpio_read_uses_gpio_service(monkeypatch):
    from mara_host.cli.commands.gpio import cmd_gpio_read

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(channel=3, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_gpio_read(args)

    assert rc == 0
    fake_ctx.gpio_service.read.assert_awaited_once_with(3)


def test_cli_servo_attach_uses_pin_as_channel(monkeypatch):
    from mara_host.cli.commands.servo import cmd_servo_attach

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(id=0, pin=18, min_us=500, max_us=2500, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_servo_attach(args)

    assert rc == 0
    fake_ctx.servo_service.attach.assert_awaited_once_with(0, channel=18, min_us=500, max_us=2500)


def test_cli_servo_set_with_pin_attaches_then_sets(monkeypatch):
    from mara_host.cli.commands.servo import cmd_servo_set
    import mara_host.cli.commands.servo as servo_cmd

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)
    monkeypatch.setattr(servo_cmd.asyncio, "sleep", AsyncMock())

    args = argparse.Namespace(id=0, angle=90, duration=250, pin=18, hold=False, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_servo_set(args)

    assert rc == 0
    fake_ctx.servo_service.attach.assert_awaited_once_with(0, channel=18, min_us=500, max_us=2500)
    fake_ctx.servo_service.set_angle.assert_awaited_once_with(0, 90, duration_ms=250)


def test_cli_servo_set_rejects_invalid_angle(monkeypatch):
    from mara_host.cli.commands.servo import cmd_servo_set

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(id=0, angle=999, duration=250, pin=None, hold=False, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_servo_set(args)

    assert rc == 1
    fake_ctx.servo_service.attach.assert_not_called()
    fake_ctx.servo_service.set_angle.assert_not_called()


def test_cli_encoder_attach_uses_encoder_service(monkeypatch):
    from mara_host.cli.commands.encoder import cmd_encoder_attach

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(id=0, pin_a=32, pin_b=33, ppr=360, gear_ratio=1.0, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_encoder_attach(args)

    assert rc == 0
    fake_ctx.encoder_service.attach.assert_awaited_once_with(0, pin_a=32, pin_b=33, ppr=360, gear_ratio=1.0)


def test_cli_encoder_read_uses_encoder_service(monkeypatch):
    from mara_host.cli.commands.encoder import cmd_encoder_read

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(id=0, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_encoder_read(args)

    assert rc == 0
    fake_ctx.encoder_service.read.assert_awaited_once_with(0)


def test_cli_encoder_reset_uses_encoder_service(monkeypatch):
    from mara_host.cli.commands.encoder import cmd_encoder_reset

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(id=0, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_encoder_reset(args)

    assert rc == 0
    fake_ctx.encoder_service.reset.assert_awaited_once_with(0)


def test_cli_imu_read_uses_imu_service(monkeypatch):
    from mara_host.cli.commands.imu import cmd_imu_read

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(format="table", port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_imu_read(args)

    assert rc == 0
    fake_ctx.imu_service.read.assert_awaited_once_with()


def test_cli_imu_calibrate_converts_delay_to_ms(monkeypatch):
    from mara_host.cli.commands.imu import cmd_imu_calibrate

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(samples=25, delay=0.2, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_imu_calibrate(args)

    assert rc == 0
    fake_ctx.imu_service.calibrate.assert_awaited_once_with(samples=25, delay_ms=200)


def test_cli_imu_set_bias_uses_imu_service(monkeypatch):
    from mara_host.cli.commands.imu import cmd_imu_set_bias

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(ax=1.0, ay=2.0, az=3.0, gx=4.0, gy=5.0, gz=6.0, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_imu_set_bias(args)

    assert rc == 0
    fake_ctx.imu_service.set_bias.assert_awaited_once_with(ax=1.0, ay=2.0, az=3.0, gx=4.0, gy=5.0, gz=6.0)


def test_cli_ultrasonic_attach_uses_service(monkeypatch):
    from mara_host.cli.commands.ultrasonic import cmd_ultrasonic_attach

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(id=0, trig=25, echo=26, max_distance=400.0, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_ultrasonic_attach(args)

    assert rc == 0
    fake_ctx.ultrasonic_service.attach.assert_awaited_once_with(0, trig_pin=25, echo_pin=26, max_distance_cm=400.0)


def test_cli_ultrasonic_read_uses_service(monkeypatch):
    from mara_host.cli.commands.ultrasonic import cmd_ultrasonic_read

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(id=0, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_ultrasonic_read(args)

    assert rc == 0
    fake_ctx.ultrasonic_service.read.assert_awaited_once_with(0)


def test_cli_parser_registers_key_control_commands():
    from mara_host.cli.main import create_parser

    parser = create_parser()
    help_text = parser.format_help()

    for name in ["gpio", "servo", "encoder", "imu", "ultrasonic", "run", "test", "build"]:
        assert name in help_text



def test_cli_ultrasonic_detach_uses_service(monkeypatch):
    from mara_host.cli.commands.ultrasonic import cmd_ultrasonic_detach

    fake_ctx = FakeCLIContext()
    _patch_ctx(monkeypatch, fake_ctx)

    args = argparse.Namespace(id=0, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_ultrasonic_detach(args)

    assert rc == 0
    fake_ctx.ultrasonic_service.detach.assert_awaited_once_with(0)


def test_cli_ultrasonic_read_reports_degraded_hardware_state(monkeypatch):
    from mara_host.cli.commands.ultrasonic import cmd_ultrasonic_read
    import mara_host.cli.commands.ultrasonic as ultrasonic_cmd

    fake_ctx = FakeCLIContext()
    fake_ctx.ultrasonic_service.read = AsyncMock(return_value=Result.success({
        "sensor_id": 0,
        "degraded": True,
        "expected": True,
        "reason": "no_echo",
    }))
    _patch_ctx(monkeypatch, fake_ctx)
    monkeypatch.setattr(ultrasonic_cmd, "print_info", MagicMock())
    monkeypatch.setattr(ultrasonic_cmd.console, "print", MagicMock())

    args = argparse.Namespace(id=0, port=None, host=None, tcp_port=None, quiet=True, verbose=False)
    rc = cmd_ultrasonic_read(args)

    assert rc == 0
    ultrasonic_cmd.print_info.assert_called_with("Ultrasonic 0: attached, but no echo was measured")
