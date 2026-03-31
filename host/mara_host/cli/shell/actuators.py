# mara_host/cli/commands/run/shell/commands/actuators.py
"""Actuator commands: led, servo, motor, dc, stepper, gpio, pwm."""

import asyncio

from .registry import command
from mara_host.cli.console import console, print_success, print_error, print_info


@command("led", "Control LED: led on/off/blink", group="Actuators")
async def cmd_led(shell, args: list[str]) -> None:
    """Control LED."""
    if not args:
        console.print("Usage: led on/off/blink")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()
    if action == "on":
        await shell.client.cmd_led_on()
        print_success("LED on")
    elif action == "off":
        await shell.client.cmd_led_off()
        print_success("LED off")
    elif action == "blink":
        count = int(args[1]) if len(args) > 1 else 3
        interval_s = float(args[2]) / 1000 if len(args) > 2 else 0.2
        for _ in range(count):
            await shell.client.cmd_led_on()
            await asyncio.sleep(interval_s)
            await shell.client.cmd_led_off()
            await asyncio.sleep(interval_s)
        print_success(f"LED blinked {count} times")
    else:
        print_error(f"Unknown LED action: {action}")


@command("servo", "Control servo: servo <id> <angle> or servo attach <id> <pin>", group="Actuators")
async def cmd_servo(shell, args: list[str]) -> None:
    """Control servo."""
    if not args:
        console.print("Usage:")
        console.print("  servo attach <id> <pin>     Attach servo to GPIO pin")
        console.print("  servo <id> <angle>          Set servo angle (0-180)")
        console.print("  servo detach <id>           Detach servo")
        return
    if not shell.require_connection():
        return

    # Handle subcommands
    if args[0] == "attach":
        if len(args) < 3:
            console.print("Usage: servo attach <id> <pin> [min_us] [max_us]")
            return
        servo_id = int(args[1])
        pin = int(args[2])
        min_us = int(args[3]) if len(args) > 3 else 500
        max_us = int(args[4]) if len(args) > 4 else 2500
        await shell.client.cmd_servo_attach(servo_id, pin, min_us, max_us)
        print_success(f"Servo {servo_id} attached to GPIO {pin}")
        return

    if args[0] == "detach":
        if len(args) < 2:
            console.print("Usage: servo detach <id>")
            return
        servo_id = int(args[1])
        await shell.client.cmd_servo_detach(servo_id)
        print_success(f"Servo {servo_id} detached")
        return

    # Default: set angle
    if len(args) < 2:
        console.print("Usage: servo <id> <angle> [duration_ms]")
        return

    servo_id = int(args[0])
    angle = float(args[1])
    duration = int(args[2]) if len(args) > 2 else 0

    await shell.client.cmd_servo_set_angle(servo_id, angle, duration)
    print_success(f"Servo {servo_id} set to {angle} degrees")


@command("motor", "Control DC motor: motor <id> <speed>", group="Actuators")
async def cmd_motor(shell, args: list[str]) -> None:
    """Control motor."""
    if len(args) < 2:
        console.print("Usage: motor <id> <speed> (-100 to 100)")
        return
    if not shell.require_connection():
        return

    motor_id = int(args[0])
    speed = float(args[1])

    # Clamp speed
    speed = max(-100, min(100, speed))

    await shell.client.cmd_dc_set_speed(motor_id, speed / 100.0)
    print_success(f"Motor {motor_id} set to {speed}%")


@command("dc", "DC motor control: dc set/stop/gains ...", group="Actuators")
async def cmd_dc(shell, args: list[str]) -> None:
    """DC motor control."""
    if not args:
        console.print("Usage:")
        console.print("  dc set <id> <speed>      Set motor speed (-1.0 to 1.0)")
        console.print("  dc stop <id>             Stop motor")
        console.print("  dc gains <id> <kp> <ki>  Set velocity PID gains")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()
    if action == "set" and len(args) >= 3:
        motor_id = int(args[1])
        speed = float(args[2])
        await shell.client.send_reliable("CMD_DC_SET_SPEED", {"motor_id": motor_id, "speed": speed})
        print_success(f"DC motor {motor_id} speed set to {speed}")
    elif action == "stop" and len(args) >= 2:
        motor_id = int(args[1])
        await shell.client.send_reliable("CMD_DC_STOP", {"motor_id": motor_id})
        print_success(f"DC motor {motor_id} stopped")
    elif action == "gains" and len(args) >= 4:
        motor_id = int(args[1])
        kp = float(args[2])
        ki = float(args[3])
        await shell.client.send_reliable("CMD_DC_SET_VEL_GAINS", {"motor_id": motor_id, "kp": kp, "ki": ki})
        print_success(f"DC motor {motor_id} gains set: kp={kp}, ki={ki}")
    else:
        print_error(f"Unknown dc action: {args}")


@command("stepper", "Stepper motor: stepper move/stop/enable/home ...", group="Actuators")
async def cmd_stepper(shell, args: list[str]) -> None:
    """Stepper motor control."""
    if not args:
        console.print("Usage:")
        console.print("  stepper move <id> <steps> [speed_rps]  Move relative steps")
        console.print("  stepper deg <id> <degrees> [speed]     Move relative degrees")
        console.print("  stepper stop <id>                      Stop motor")
        console.print("  stepper enable <id> [0/1]              Enable/disable motor")
        console.print("  stepper home <id> [speed]              Home the motor")
        console.print("  stepper pos <id>                       Get position")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()
    if action == "move" and len(args) >= 3:
        stepper_id = int(args[1])
        steps = int(args[2])
        speed = float(args[3]) if len(args) > 3 else 1.0
        await shell.client.send_reliable("CMD_STEPPER_MOVE_REL", {"stepper_id": stepper_id, "steps": steps, "speed_rps": speed})
        print_success(f"Stepper {stepper_id} moving {steps} steps")
    elif action == "deg" and len(args) >= 3:
        stepper_id = int(args[1])
        degrees = float(args[2])
        speed = float(args[3]) if len(args) > 3 else 1.0
        await shell.client.send_reliable("CMD_STEPPER_MOVE_DEG", {"stepper_id": stepper_id, "degrees": degrees, "speed_rps": speed})
        print_success(f"Stepper {stepper_id} moving {degrees} degrees")
    elif action == "stop" and len(args) >= 2:
        stepper_id = int(args[1])
        await shell.client.send_reliable("CMD_STEPPER_STOP", {"stepper_id": stepper_id})
        print_success(f"Stepper {stepper_id} stopped")
    elif action == "enable" and len(args) >= 2:
        stepper_id = int(args[1])
        enable = bool(int(args[2])) if len(args) > 2 else True
        await shell.client.send_reliable("CMD_STEPPER_ENABLE", {"stepper_id": stepper_id, "enable": enable})
        print_success(f"Stepper {stepper_id} {'enabled' if enable else 'disabled'}")
    elif action == "home" and len(args) >= 2:
        stepper_id = int(args[1])
        speed = float(args[2]) if len(args) > 2 else 0.5
        await shell.client.send_reliable("CMD_STEPPER_HOME", {"stepper_id": stepper_id, "speed_rps": speed})
        print_success(f"Stepper {stepper_id} homing")
    elif action == "pos" and len(args) >= 2:
        stepper_id = int(args[1])
        await shell.client.send_reliable("CMD_STEPPER_GET_POSITION", {"stepper_id": stepper_id})
        print_info(f"Position requested for stepper {stepper_id} (check events)")
    else:
        print_error(f"Unknown stepper action: {args}")


@command("gpio", "Control GPIO: gpio <channel> high/low/read", group="Actuators")
async def cmd_gpio(shell, args: list[str]) -> None:
    """Control GPIO."""
    if len(args) < 2:
        console.print("Usage: gpio <channel> high/low/read")
        return
    if not shell.require_connection():
        return

    channel = int(args[0])
    action = args[1].lower()

    if action == "high":
        await shell.client.cmd_gpio_write(channel, True)
        print_success(f"GPIO channel {channel} set HIGH")
    elif action == "low":
        await shell.client.cmd_gpio_write(channel, False)
        print_success(f"GPIO channel {channel} set LOW")
    elif action == "read":
        # Note: This would need async response handling
        print_info(f"GPIO read not yet implemented in shell")
    else:
        print_error(f"Unknown GPIO action: {action}")


@command("pwm", "PWM control: pwm <channel> <duty> [freq]", group="Actuators")
async def cmd_pwm(shell, args: list[str]) -> None:
    """PWM control."""
    if len(args) < 2:
        console.print("Usage: pwm <channel> <duty> [freq_hz]")
        console.print("  duty: 0.0 to 1.0")
        console.print("  freq: frequency in Hz (default: 1000)")
        return
    if not shell.require_connection():
        return

    channel = int(args[0])
    duty = float(args[1])
    freq = float(args[2]) if len(args) > 2 else 1000.0
    await shell.client.send_reliable("CMD_PWM_SET", {"channel": channel, "duty": duty, "freq_hz": freq})
    print_success(f"PWM channel {channel} set to {duty*100:.1f}% duty @ {freq}Hz")
