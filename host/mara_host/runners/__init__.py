# mara_host/runners/__init__.py
"""
DEPRECATED: The runners/ directory has been reorganized.

Files have moved to:
- mara_host/examples/     - Educational examples
- mara_host/benchmarks/   - Performance benchmarks

New Locations:
-------------
Connection Examples:
    examples/connections/serial_basic.py     (was: run_serial_client.py)
    examples/connections/tcp_basic.py        (was: run_tcp_client.py)
    examples/connections/can_basic.py        (was: run_can_client.py)

Shell Examples:
    examples/shells/interactive_shell.py     (was: interactive_shell.py)
    examples/shells/serial_shell.py          (was: serial_interactive_shell.py)
    examples/shells/bluetooth_shell.py       (was: bluetooth_shell.py)
    examples/shells/telemetry_shell.py       (was: telemetry_shell.py)

Motor Examples:
    examples/motors/pid_test.py              (was: pid_tst.py)
    examples/motors/pid_sweep.py             (was: pid_sweep_tst.py)
    examples/motors/stepper_test.py          (was: stepper_tst.py)

Streaming Examples:
    examples/streaming/stream_basic.py       (was: stream_runner.py)

Recording Examples:
    examples/recording/record_session.py     (was: record_short_session.py)
    examples/recording/replay_metrics.py     (was: replay_to_metrics.py)

Application Examples:
    examples/applications/pill_carousel.py   (was: pill_carousel.py)
    examples/applications/pill_gui.py        (was: pill_gui.py)
    examples/applications/camera_basic.py    (was: run_camera.py)
    examples/applications/camera_host.py     (was: run_camera_host.py)
    examples/applications/camera_detection.py (was: run_camera_boxes.py)
    examples/applications/detection.py       (was: run_detection.py)
    examples/applications/mqtt_nodes.py      (was: run_mqtt_nodes.py)

Benchmarks:
    benchmarks/latency/basic_latency.py      (was: latency_tst.py)
    benchmarks/latency/led_latency.py        (was: led_latency_tst.py)
    benchmarks/latency/dc_motor_latency.py   (was: dc_latency_tst.py)
    benchmarks/latency/run_benchmarks.py     (was: run_latency_benchmarks.py)
    benchmarks/commands/send_all.py          (was: send_all_commands.py)

Migration:
---------
Update your imports:
    # Old
    from mara_host.runners.interactive_shell import main

    # New
    from mara_host.examples.shells.interactive_shell import main

This directory will be removed in a future release.
"""
import warnings

warnings.warn(
    "mara_host.runners is deprecated. "
    "Use mara_host.examples or mara_host.benchmarks instead. "
    "See mara_host.runners.__doc__ for migration guide.",
    DeprecationWarning,
    stacklevel=2
)

# Backward compatibility imports (will emit additional warnings)
def __getattr__(name: str):
    """Provide backward compatibility with deprecation warnings."""
    import importlib

    # Map old names to new locations
    _MIGRATIONS = {
        "interactive_shell": "mara_host.examples.shells.interactive_shell",
        "serial_interactive_shell": "mara_host.examples.shells.serial_shell",
        "bluetooth_shell": "mara_host.examples.shells.bluetooth_shell",
        "telemetry_shell": "mara_host.examples.shells.telemetry_shell",
        "run_serial_client": "mara_host.examples.connections.serial_basic",
        "run_tcp_client": "mara_host.examples.connections.tcp_basic",
        "run_can_client": "mara_host.examples.connections.can_basic",
        "pid_tst": "mara_host.examples.motors.pid_test",
        "pid_sweep_tst": "mara_host.examples.motors.pid_sweep",
        "stepper_tst": "mara_host.examples.motors.stepper_test",
        "stream_runner": "mara_host.examples.streaming.stream_basic",
        "record_short_session": "mara_host.examples.recording.record_session",
        "replay_to_metrics": "mara_host.examples.recording.replay_metrics",
        "pill_carousel": "mara_host.examples.applications.pill_carousel",
        "pill_gui": "mara_host.examples.applications.pill_gui",
        "run_camera": "mara_host.examples.applications.camera_basic",
        "run_camera_host": "mara_host.examples.applications.camera_host",
        "run_camera_boxes": "mara_host.examples.applications.camera_detection",
        "run_detection": "mara_host.examples.applications.detection",
        "run_mqtt_nodes": "mara_host.examples.applications.mqtt_nodes",
        "latency_tst": "mara_host.benchmarks.latency.basic_latency",
        "led_latency_tst": "mara_host.benchmarks.latency.led_latency",
        "dc_latency_tst": "mara_host.benchmarks.latency.dc_motor_latency",
        "run_latency_benchmarks": "mara_host.benchmarks.latency.run_benchmarks",
        "send_all_commands": "mara_host.benchmarks.commands.send_all",
    }

    if name in _MIGRATIONS:
        new_path = _MIGRATIONS[name]
        warnings.warn(
            f"mara_host.runners.{name} has moved to {new_path}",
            DeprecationWarning,
            stacklevel=2
        )
        return importlib.import_module(new_path)

    raise AttributeError(f"module 'mara_host.runners' has no attribute '{name}'")
