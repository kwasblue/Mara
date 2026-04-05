#!/usr/bin/env python3
"""MCU firmware build and test tool.

Compiles ESP32 firmware using PlatformIO and runs unit tests.

Usage:
    python build_firmware.py build -e esp32_usb
    python build_firmware.py build -e esp32_base --features wifi,ota,dc_motor
    python build_firmware.py test --native
    python build_firmware.py upload -g  # generate + compile + flash
    python build_firmware.py upload -e esp32_base --features wifi,ota,servo
"""

from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

# Path to MCU project (relative to monorepo structure)
_TOOLS_DIR = Path(__file__).resolve().parent
MCU_PROJECT = _TOOLS_DIR.parent.parent.parent / "firmware" / "mcu"

# Available environments from platformio.ini + cmake Linux environments
ENVIRONMENTS = {
    "esp32_minimal", "esp32_motors", "esp32_sensors",
    "esp32_control", "esp32_full", "esp32_usb", "esp32_ota",
    "esp32_base", "native", "esp32_test",
    "linux_minimal", "linux_motors", "linux_full",
}

# Import from single source of truth (mara_build.yaml via build_profiles)
from mara_host.core.build_profiles import (
    get_profile_names,
    FEATURE_TO_MACRO as FEATURES,
    FEATURE_ALIASES,
    parse_features,
    features_to_build_flags as features_to_flags,
)

# For backwards compatibility, expose PRESETS as profile names
PRESETS = {name: name for name in get_profile_names()}


def _find_pio() -> list[str]:
    """Return the command prefix to invoke PlatformIO."""
    pio = shutil.which("pio") or shutil.which("platformio")
    if pio:
        return [pio]
    # Fallback: run via the current Python interpreter
    return [sys.executable, "-m", "platformio"]


def run_pio(args: list[str], verbose: bool = False,
            extra_flags: list[str] | None = None) -> int:
    """Run PlatformIO CLI command."""
    cmd = _find_pio() + args

    # Set up environment with build flags
    env = os.environ.copy()
    if extra_flags:
        # PlatformIO reads PLATFORMIO_BUILD_FLAGS as space-separated flags
        flags_str = " ".join(extra_flags)
        env["PLATFORMIO_BUILD_FLAGS"] = flags_str
        print(f"[build_firmware] Build flags: {flags_str}")

    print(f"[build_firmware] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=MCU_PROJECT, env=env)
    return result.returncode


def generate() -> None:
    """Run all code generators."""
    print("[build_firmware] Running code generators...")
    from generate_all import main as generate_all
    generate_all()


def build(env: str, verbose: bool = False,
          features: dict[str, bool] | None = None) -> int:
    """Compile firmware."""
    print(f"[build_firmware] Building environment: {env}")
    if features:
        enabled = [k for k, v in features.items() if v]
        print(f"[build_firmware] Features: {', '.join(enabled)}")

    args = ["run", "-e", env]
    if verbose:
        args.append("-v")

    return run_pio(args, verbose, features_to_flags(features))


def _find_esptool() -> str | None:
    """Find a usable esptool entrypoint."""
    candidates = [
        shutil.which("esptool.py"),
        shutil.which("esptool"),
        str(Path.home() / ".platformio" / "packages" / "tool-esptoolpy" / "esptool.py"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _direct_upload(env: str, port: str, upload_baud: int) -> int:
    """Flash via esptool directly using PlatformIO build artifacts."""
    build_dir = MCU_PROJECT / ".pio" / "build" / env
    bootloader = build_dir / "bootloader.bin"
    partitions = build_dir / "partitions.bin"
    firmware = build_dir / "firmware.bin"
    boot_app0 = Path.home() / ".platformio" / "packages" / "framework-arduinoespressif32" / "tools" / "partitions" / "boot_app0.bin"

    missing = [str(p) for p in (bootloader, partitions, firmware, boot_app0) if not p.exists()]
    if missing:
        print("[build_firmware] Missing flash artifacts:")
        for path in missing:
            print(f"  - {path}")
        return 1

    esptool = _find_esptool()
    if not esptool:
        print("[build_firmware] Could not find esptool")
        return 1

    cmd = [
        sys.executable, esptool,
        "--chip", "esp32",
        "--port", port,
        "--baud", str(upload_baud),
        "--before", "default_reset",
        "--after", "hard_reset",
        "write_flash", "-z",
        "0x1000", str(bootloader),
        "0x8000", str(partitions),
        "0xe000", str(boot_app0),
        "0x10000", str(firmware),
    ]
    print(f"[build_firmware] Running direct flash: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=MCU_PROJECT)
    return result.returncode


def upload(env: str, verbose: bool = False,
           features: dict[str, bool] | None = None,
           port: str | None = None,
           upload_baud: int | None = None,
           direct: bool = False) -> int:
    """Compile and upload firmware.

    Args:
        env: PlatformIO environment
        verbose: Verbose output
        features: Feature flags dict
        port: Serial port for upload (auto-detect if None)
        upload_baud: If set, use direct esptool flashing at this baud rate
        direct: Skip PlatformIO upload target and flash directly with esptool
    """
    print(f"[build_firmware] Uploading to environment: {env}")
    if port:
        print(f"[build_firmware] Upload port: {port}")
    if upload_baud:
        print(f"[build_firmware] Upload baud: {upload_baud}")
    if features:
        enabled = [k for k, v in features.items() if v]
        print(f"[build_firmware] Features: {', '.join(enabled)}")

    if direct or upload_baud:
        build_rc = build(env, verbose, features)
        if build_rc != 0:
            return build_rc
        if not port:
            print("[build_firmware] Direct flash requires --port")
            return 1
        return _direct_upload(env, port, upload_baud or 115200)

    args = ["run", "-e", env, "-t", "upload"]
    if port:
        args.extend(["--upload-port", port])
    if verbose:
        args.append("-v")

    return run_pio(args, verbose, features_to_flags(features))


def test(native: bool = True, device: bool = False,
         filter_pattern: str | None = None, verbose: bool = False) -> int:
    """Run unit tests."""
    envs = []
    if native:
        envs.append("native")
    if device:
        envs.append("esp32_test")

    if not envs:
        envs = ["native"]  # default

    for env in envs:
        print(f"[build_firmware] Running tests: {env}")
        args = ["test", "-e", env]
        if filter_pattern:
            args.extend(["-f", filter_pattern])
        if verbose:
            args.append("-v")

        rc = run_pio(args, verbose)
        if rc != 0:
            return rc
    return 0


def clean(env: str | None = None) -> int:
    """Clean build artifacts."""
    args = ["run", "-t", "clean"]
    if env:
        args.extend(["-e", env])
    return run_pio(args)


def list_features() -> None:
    """Print available features and presets."""
    from mara_host.core.build_profiles import get_profile, get_profile_names

    print("\nAvailable features:")
    print("-" * 40)

    categories = {
        "Transport": ["wifi", "ble", "uart_transport", "mqtt_transport"],
        "Motors": ["servo", "stepper", "dc_motor", "encoder", "motion_controller"],
        "Sensors": ["ultrasonic", "imu", "lidar"],
        "Control": ["signal_bus", "control_kernel", "pid_controller", "state_space",
                    "observer", "control_module"],
        "System": ["ota", "telemetry", "heartbeat", "logging", "identity", "audio", "benchmark"],
    }

    for category, feats in categories.items():
        print(f"\n{category}:")
        for feat in feats:
            if feat in FEATURES:
                print(f"  {feat:20} -> {FEATURES[feat]}")
            # Show aliases
            for alias, canonical in FEATURE_ALIASES.items():
                if canonical == feat:
                    print(f"    (alias: {alias})")

    print("\n\nProfiles (from mara_build.yaml):")
    print("-" * 40)
    for profile_name in get_profile_names():
        profile = get_profile(profile_name)
        enabled = [k for k, v in profile.items() if v]
        print(f"\n{profile_name}:")
        print(f"  {', '.join(enabled)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MCU firmware build and test tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  build_firmware.py build -e esp32_usb
  build_firmware.py build -e esp32_base --features wifi,ota,dc_motor
  build_firmware.py build -e esp32_base --features full --no-features audio,lidar
  build_firmware.py upload -e esp32_base --features motors
  build_firmware.py features  # list available features
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Common options
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-v", "--verbose", action="store_true")
    common.add_argument("-g", "--generate", action="store_true",
                        help="Run code generators first")

    # Feature options (for build/upload)
    feature_opts = argparse.ArgumentParser(add_help=False)
    feature_opts.add_argument(
        "--features",
        metavar="LIST",
        help="Comma-separated features to enable (e.g., wifi,ota,dc_motor) "
             "or preset name (minimal, motors, sensors, control, full)"
    )
    feature_opts.add_argument(
        "--no-features",
        metavar="LIST",
        help="Comma-separated features to disable (use with presets)"
    )

    # build command
    build_p = subparsers.add_parser("build", parents=[common, feature_opts])
    build_p.add_argument("-e", "--env", default="esp32_usb")

    # upload command
    upload_p = subparsers.add_parser("upload", parents=[common, feature_opts])
    upload_p.add_argument("-e", "--env", default="esp32_usb")

    # test command
    test_p = subparsers.add_parser("test", parents=[common])
    test_p.add_argument("--native", action="store_true", default=True)
    test_p.add_argument("--device", action="store_true")
    test_p.add_argument("-f", "--filter", dest="filter_pattern")

    # clean command
    clean_p = subparsers.add_parser("clean", parents=[common])
    clean_p.add_argument("-e", "--env", default=None)

    # features command (list available)
    subparsers.add_parser("features", help="List available features and presets")

    args = parser.parse_args()

    # Handle features command
    if args.command == "features":
        list_features()
        return 0

    # Handle generate flag
    if getattr(args, "generate", False):
        generate()

    # Parse feature flags
    features = parse_features(
        getattr(args, "features", None),
        getattr(args, "no_features", None)
    )

    # Dispatch
    if args.command == "build" or args.command is None:
        return build(getattr(args, "env", "esp32_usb"),
                     getattr(args, "verbose", False), features)
    elif args.command == "upload":
        return upload(args.env, args.verbose, features)
    elif args.command == "test":
        return test(args.native, args.device, args.filter_pattern, args.verbose)
    elif args.command == "clean":
        return clean(getattr(args, "env", None))

    return 0


if __name__ == "__main__":
    sys.exit(main())
