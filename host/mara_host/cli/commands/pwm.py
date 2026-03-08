# mara_host/cli/commands/pwm.py
"""PWM direct control commands.

Examples:
    mara pwm set 0 0.5 --freq 1000   # Set channel 0 to 50% duty at 1kHz
    mara pwm duty 0 0.75             # Set channel 0 to 75% duty
    mara pwm percent 0 50            # Set channel 0 to 50% (as integer)
    mara pwm stop 0                  # Stop PWM on channel 0
    mara pwm fade 0                  # Fade channel 0 in/out (demo)
"""

import argparse
import asyncio
import time
import math

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register PWM control commands."""
    pwm_parser = subparsers.add_parser(
        "pwm",
        help="PWM direct control",
        description="Control PWM channels directly",
    )

    pwm_sub = pwm_parser.add_subparsers(
        dest="pwm_cmd",
        title="pwm commands",
        metavar="<subcommand>",
    )

    def add_port_arg(parser):
        parser.add_argument(
            "-p", "--port",
            default="/dev/cu.usbserial-0001",
            help="Serial port",
        )

    # pwm set <channel> <duty> [--freq]
    set_p = pwm_sub.add_parser(
        "set",
        help="Set PWM duty cycle and optionally frequency",
    )
    set_p.add_argument("channel", type=int, help="PWM channel (0-15)")
    set_p.add_argument("duty", type=float, help="Duty cycle (0.0-1.0)")
    set_p.add_argument(
        "--freq",
        type=int,
        default=1000,
        help="Frequency in Hz (default: 1000)",
    )
    add_port_arg(set_p)
    set_p.set_defaults(func=cmd_pwm_set)

    # pwm duty <channel> <duty>
    duty_p = pwm_sub.add_parser(
        "duty",
        help="Set duty cycle only (0.0-1.0)",
    )
    duty_p.add_argument("channel", type=int, help="PWM channel")
    duty_p.add_argument("duty", type=float, help="Duty cycle (0.0-1.0)")
    add_port_arg(duty_p)
    duty_p.set_defaults(func=cmd_pwm_duty)

    # pwm percent <channel> <percent>
    pct_p = pwm_sub.add_parser(
        "percent",
        help="Set duty as percentage (0-100)",
    )
    pct_p.add_argument("channel", type=int, help="PWM channel")
    pct_p.add_argument("percent", type=float, help="Duty as percentage (0-100)")
    add_port_arg(pct_p)
    pct_p.set_defaults(func=cmd_pwm_percent)

    # pwm stop <channel>
    stop_p = pwm_sub.add_parser(
        "stop",
        help="Stop PWM (set duty to 0)",
    )
    stop_p.add_argument("channel", type=int, help="PWM channel")
    add_port_arg(stop_p)
    stop_p.set_defaults(func=cmd_pwm_stop)

    # pwm fade <channel>
    fade_p = pwm_sub.add_parser(
        "fade",
        help="Fade PWM in/out (demo)",
    )
    fade_p.add_argument("channel", type=int, help="PWM channel")
    fade_p.add_argument(
        "--cycles",
        type=int,
        default=3,
        help="Number of fade cycles (default: 3)",
    )
    fade_p.add_argument(
        "--duration",
        type=float,
        default=2.0,
        help="Cycle duration in seconds (default: 2.0)",
    )
    add_port_arg(fade_p)
    fade_p.set_defaults(func=cmd_pwm_fade)

    pwm_parser.set_defaults(func=lambda args: cmd_help(pwm_parser))


def cmd_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


async def _connect_and_run(port: str, command: str, payload: dict) -> tuple[bool, str]:
    """Connect to robot, send command, and return result."""
    from mara_host.services.transport import ConnectionService, ConnectionConfig, TransportType

    config = ConnectionConfig(
        transport_type=TransportType.SERIAL,
        port=port,
        baudrate=115200,
    )

    conn = ConnectionService(config)
    try:
        await conn.connect()
        ok, error = await conn.client.send_reliable(command, payload)
        return ok, error or ""
    finally:
        await conn.disconnect()


def _run_async(coro):
    return asyncio.run(coro)


def cmd_pwm_set(args: argparse.Namespace) -> int:
    """Set PWM duty and frequency."""
    if not 0.0 <= args.duty <= 1.0:
        print_error(f"Duty must be 0.0-1.0 (got {args.duty})")
        return 1

    payload = {
        "channel": args.channel,
        "duty": args.duty,
        "freq_hz": args.freq,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_PWM_SET", payload))
        if ok:
            print_success(f"PWM {args.channel}: {args.duty*100:.1f}% @ {args.freq}Hz")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_pwm_duty(args: argparse.Namespace) -> int:
    """Set PWM duty only."""
    if not 0.0 <= args.duty <= 1.0:
        print_error(f"Duty must be 0.0-1.0 (got {args.duty})")
        return 1

    payload = {
        "channel": args.channel,
        "duty": args.duty,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_PWM_SET", payload))
        if ok:
            print_success(f"PWM {args.channel}: {args.duty*100:.1f}%")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_pwm_percent(args: argparse.Namespace) -> int:
    """Set PWM as percentage."""
    if not 0 <= args.percent <= 100:
        print_error(f"Percent must be 0-100 (got {args.percent})")
        return 1

    duty = args.percent / 100.0
    payload = {
        "channel": args.channel,
        "duty": duty,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_PWM_SET", payload))
        if ok:
            print_success(f"PWM {args.channel}: {args.percent:.0f}%")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_pwm_stop(args: argparse.Namespace) -> int:
    """Stop PWM."""
    payload = {
        "channel": args.channel,
        "duty": 0.0,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_PWM_SET", payload))
        if ok:
            print_success(f"PWM {args.channel}: stopped")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_pwm_fade(args: argparse.Namespace) -> int:
    """Fade PWM in/out."""
    console.print(f"[bold cyan]Fading PWM {args.channel}[/bold cyan]")
    console.print(f"  Cycles: {args.cycles}")
    console.print(f"  Duration: {args.duration}s per cycle")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    steps = 50
    step_delay = args.duration / steps

    try:
        for cycle in range(args.cycles):
            # Fade in
            for i in range(steps):
                duty = (math.sin(math.pi * i / steps - math.pi/2) + 1) / 2
                payload = {"channel": args.channel, "duty": duty}
                _run_async(_connect_and_run(args.port, "CMD_PWM_SET", payload))
                time.sleep(step_delay)

            # Fade out
            for i in range(steps):
                duty = (math.sin(math.pi * i / steps + math.pi/2) + 1) / 2
                payload = {"channel": args.channel, "duty": duty}
                _run_async(_connect_and_run(args.port, "CMD_PWM_SET", payload))
                time.sleep(step_delay)

        # Ensure off at end
        payload = {"channel": args.channel, "duty": 0.0}
        _run_async(_connect_and_run(args.port, "CMD_PWM_SET", payload))

        print_success(f"PWM {args.channel}: fade complete")
    except KeyboardInterrupt:
        payload = {"channel": args.channel, "duty": 0.0}
        _run_async(_connect_and_run(args.port, "CMD_PWM_SET", payload))
        console.print("\n[dim]Fade interrupted[/dim]")
    except Exception as e:
        print_error(f"Error: {e}")
        return 1

    return 0
