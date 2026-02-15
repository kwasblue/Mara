import asyncio

from robot_host.core.robot_runtime import build_runtime


async def main() -> None:
    # Build runtime using the default profile in config/robot_profile_default.yaml
    rt = await build_runtime(profile="default")

    print("\n=== RobotRuntime built ===")
    print(f"  bus       : {rt.bus}")
    print(f"  client    : {rt.client}")
    print(f"  telemetry : {rt.telemetry is not None}")
    print(f"  encoder   : {rt.encoder is not None}")
    print(f"  motion    : {rt.motion is not None}")
    print(f"  modes     : {rt.modes is not None}")
    print(f"  telem_ctl : {rt.telemetry_ctl is not None}")
    print(f"  log_ctl   : {rt.logging_ctl is not None}")

    # --- Basic tests ---

    # 1) Turn telemetry ON at 10 Hz for a bit, then OFF
    if rt.telemetry_ctl is not None:
        print("\n[TEST] Enabling telemetry at 10 Hz (100 ms)")
        await rt.telemetry_ctl.set_interval(100)
    else:
        print("\n[TEST] TelemetryControlModule not available")

    # 2) Make sure modes work (IDLE -> ARMED -> ACTIVE)
    if rt.modes is not None:
        print("[TEST] Setting mode=ARMED")
        await rt.modes.set_mode("ARMED")
        await asyncio.sleep(0.2)

        print("[TEST] Setting mode=ACTIVE")
        await rt.modes.set_mode("ACTIVE")
    else:
        print("[TEST] ModeHostModule not available")

    # 3) Try encoder attach + read, if the module is enabled
    if rt.encoder is not None:
        print("[TEST] Attaching encoder with defaults...")
        await rt.encoder.attach()
        await asyncio.sleep(0.2)

        print("[TEST] Requesting encoder read...")
        await rt.encoder.read()
    else:
        print("[TEST] EncoderHostModule not available")

    # 4) Let things run for a bit so you can see telemetry prints
    print("\n[TEST] Letting runtime idle for 5 seconds...")
    await asyncio.sleep(5.0)

    # 5) Turn telemetry OFF before exit
    if rt.telemetry_ctl is not None:
        print("\n[TEST] Disabling telemetry (interval=0)")
        await rt.telemetry_ctl.set_interval(0)

    print("\n[TEST] Done. You can Ctrl+C to stop if still running.")


if __name__ == "__main__":
    asyncio.run(main())
