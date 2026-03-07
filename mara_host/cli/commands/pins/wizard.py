# mara_host/cli/commands/pins/wizard.py
"""
Guided pin configuration wizards.
"""

import argparse

from rich.prompt import Prompt, IntPrompt, Confirm

from mara_host.cli.console import (
    console,
    print_info,
    print_warning,
)
from mara_host.services.pins import PinService
from mara_host.cli.commands.pins._common import do_assign


def cmd_wizard(args: argparse.Namespace) -> int:
    """Guided setup wizard for common pin configurations."""
    preset = getattr(args, 'preset', None)

    console.print()
    console.print("[bold cyan]Pin Configuration Wizard[/bold cyan]")
    console.print()

    if not preset:
        console.print("Available configurations:")
        console.print()
        console.print("  [cyan]motor[/cyan]     DC motor with direction control (PWM + IN1 + IN2)")
        console.print("  [cyan]encoder[/cyan]   Quadrature encoder (A + B channels)")
        console.print("  [cyan]stepper[/cyan]   Stepper motor (STEP + DIR + EN)")
        console.print("  [cyan]servo[/cyan]     Servo motor (single PWM pin)")
        console.print("  [cyan]i2c[/cyan]       I2C bus (SDA + SCL)")
        console.print("  [cyan]spi[/cyan]       SPI bus (MOSI + MISO + CLK + CS)")
        console.print("  [cyan]uart[/cyan]      UART (TX + RX)")
        console.print()
        preset = Prompt.ask(
            "Select configuration",
            choices=["motor", "encoder", "stepper", "servo", "i2c", "spi", "uart"],
        )

    wizards = {
        "motor": _wizard_motor,
        "encoder": _wizard_encoder,
        "stepper": _wizard_stepper,
        "servo": _wizard_servo,
        "i2c": _wizard_i2c,
        "spi": _wizard_spi,
        "uart": _wizard_uart,
    }

    wizard_func = wizards.get(preset)
    if wizard_func:
        return wizard_func()

    return 0


def _wizard_motor() -> int:
    """Configure a DC motor using PinService recommendations."""
    service = PinService()

    console.print("[bold]DC Motor Configuration[/bold]")
    console.print("[dim]Requires: PWM pin + 2 direction pins (IN1, IN2)[/dim]")
    console.print()

    motor_id = Prompt.ask("Motor identifier", default="LEFT")
    motor_id = motor_id.upper()

    rec = service.recommend_motor_pins(motor_id)

    if rec.warnings:
        for w in rec.warnings:
            print_warning(w)

    console.print(f"[dim]Suggested pins based on current assignments[/dim]")

    pwm_default = rec.suggested_assignments.get(f"MOTOR_{motor_id}_PWM", 0)
    in1_default = rec.suggested_assignments.get(f"MOTOR_{motor_id}_IN1", 0)
    in2_default = rec.suggested_assignments.get(f"MOTOR_{motor_id}_IN2", 0)

    pwm_gpio = IntPrompt.ask(f"PWM pin for MOTOR_{motor_id}_PWM", default=pwm_default)
    in1_gpio = IntPrompt.ask(f"IN1 pin for MOTOR_{motor_id}_IN1", default=in1_default)
    in2_gpio = IntPrompt.ask(f"IN2 pin for MOTOR_{motor_id}_IN2", default=in2_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  MOTOR_{motor_id}_PWM = GPIO {pwm_gpio}")
    console.print(f"  MOTOR_{motor_id}_IN1 = GPIO {in1_gpio}")
    console.print(f"  MOTOR_{motor_id}_IN2 = GPIO {in2_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        do_assign(f"MOTOR_{motor_id}_PWM", pwm_gpio, force=True)
        do_assign(f"MOTOR_{motor_id}_IN1", in1_gpio, force=True)
        do_assign(f"MOTOR_{motor_id}_IN2", in2_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")
    else:
        console.print("[dim]Cancelled.[/dim]")

    return 0


def _wizard_encoder() -> int:
    """Configure a quadrature encoder using PinService recommendations."""
    service = PinService()

    console.print("[bold]Quadrature Encoder Configuration[/bold]")
    console.print("[dim]Requires: 2 input pins (A + B channels)[/dim]")
    console.print()

    enc_id = Prompt.ask("Encoder identifier (e.g., 0, LEFT)", default="0")
    enc_id = enc_id.upper()

    rec = service.recommend_encoder_pins(enc_id)

    a_default = rec.suggested_assignments.get(f"ENC{enc_id}_A", 0)
    b_default = rec.suggested_assignments.get(f"ENC{enc_id}_B", 0)

    a_gpio = IntPrompt.ask(f"A channel pin for ENC{enc_id}_A", default=a_default)
    b_gpio = IntPrompt.ask(f"B channel pin for ENC{enc_id}_B", default=b_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  ENC{enc_id}_A = GPIO {a_gpio}")
    console.print(f"  ENC{enc_id}_B = GPIO {b_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        do_assign(f"ENC{enc_id}_A", a_gpio, force=True)
        do_assign(f"ENC{enc_id}_B", b_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0


def _wizard_stepper() -> int:
    """Configure a stepper motor using PinService recommendations."""
    service = PinService()

    console.print("[bold]Stepper Motor Configuration[/bold]")
    console.print("[dim]Requires: STEP, DIR, and optionally EN pins[/dim]")
    console.print()

    stepper_id = Prompt.ask("Stepper identifier", default="0")
    stepper_id = stepper_id.upper()

    rec = service.recommend_stepper_pins(stepper_id)

    step_default = rec.suggested_assignments.get(f"STEPPER{stepper_id}_STEP", 0)
    dir_default = rec.suggested_assignments.get(f"STEPPER{stepper_id}_DIR", 0)
    en_default = rec.suggested_assignments.get(f"STEPPER{stepper_id}_EN", 0)

    step_gpio = IntPrompt.ask("STEP pin", default=step_default)
    dir_gpio = IntPrompt.ask("DIR pin", default=dir_default)

    use_en = Confirm.ask("Add ENABLE pin?", default=True)
    en_gpio = None
    if use_en:
        en_gpio = IntPrompt.ask("EN pin", default=en_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  STEPPER{stepper_id}_STEP = GPIO {step_gpio}")
    console.print(f"  STEPPER{stepper_id}_DIR = GPIO {dir_gpio}")
    if en_gpio:
        console.print(f"  STEPPER{stepper_id}_EN = GPIO {en_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        do_assign(f"STEPPER{stepper_id}_STEP", step_gpio, force=True)
        do_assign(f"STEPPER{stepper_id}_DIR", dir_gpio, force=True)
        if en_gpio:
            do_assign(f"STEPPER{stepper_id}_EN", en_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0


def _wizard_servo() -> int:
    """Configure a servo motor using PinService recommendations."""
    service = PinService()

    console.print("[bold]Servo Motor Configuration[/bold]")
    console.print("[dim]Requires: 1 PWM-capable pin[/dim]")
    console.print()

    servo_id = Prompt.ask("Servo identifier", default="0")
    servo_id = servo_id.upper()

    rec = service.recommend_servo_pins(servo_id)
    sig_default = rec.suggested_assignments.get(f"SERVO{servo_id}_SIG", 0)

    sig_gpio = IntPrompt.ask("Signal pin", default=sig_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  SERVO{servo_id}_SIG = GPIO {sig_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        do_assign(f"SERVO{servo_id}_SIG", sig_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0


def _wizard_i2c() -> int:
    """Configure I2C bus using PinService recommendations."""
    service = PinService()

    console.print("[bold]I2C Bus Configuration[/bold]")
    console.print("[dim]Standard pins: GPIO 21 (SDA), GPIO 22 (SCL)[/dim]")
    console.print()

    rec = service.recommend_i2c_pins()

    sda_default = rec.suggested_assignments.get("I2C_SDA", 21)
    scl_default = rec.suggested_assignments.get("I2C_SCL", 22)

    sda_gpio = IntPrompt.ask("SDA pin", default=sda_default)
    scl_gpio = IntPrompt.ask("SCL pin", default=scl_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  I2C_SDA = GPIO {sda_gpio}")
    console.print(f"  I2C_SCL = GPIO {scl_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        do_assign("I2C_SDA", sda_gpio, force=True)
        do_assign("I2C_SCL", scl_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0


def _wizard_spi() -> int:
    """Configure SPI bus using PinService recommendations."""
    service = PinService()

    console.print("[bold]SPI Bus Configuration[/bold]")
    console.print("[dim]Standard VSPI pins: MOSI=23, MISO=19, CLK=18, CS=5[/dim]")
    console.print()

    rec = service.recommend_spi_pins()

    mosi_default = rec.suggested_assignments.get("SPI_MOSI", 23)
    miso_default = rec.suggested_assignments.get("SPI_MISO", 19)
    clk_default = rec.suggested_assignments.get("SPI_CLK", 18)
    cs_default = rec.suggested_assignments.get("SPI_CS", 5)

    mosi_gpio = IntPrompt.ask("MOSI pin", default=mosi_default)
    miso_gpio = IntPrompt.ask("MISO pin", default=miso_default)
    clk_gpio = IntPrompt.ask("CLK pin", default=clk_default)
    cs_gpio = IntPrompt.ask("CS pin", default=cs_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  SPI_MOSI = GPIO {mosi_gpio}")
    console.print(f"  SPI_MISO = GPIO {miso_gpio}")
    console.print(f"  SPI_CLK = GPIO {clk_gpio}")
    console.print(f"  SPI_CS = GPIO {cs_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        do_assign("SPI_MOSI", mosi_gpio, force=True)
        do_assign("SPI_MISO", miso_gpio, force=True)
        do_assign("SPI_CLK", clk_gpio, force=True)
        do_assign("SPI_CS", cs_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0


def _wizard_uart() -> int:
    """Configure UART using PinService recommendations."""
    service = PinService()

    console.print("[bold]UART Configuration[/bold]")
    console.print("[dim]UART2 default pins: TX=17, RX=16[/dim]")
    console.print()

    uart_num = Prompt.ask("UART number", default="1")

    rec = service.recommend_uart_pins(uart_num)

    tx_default = rec.suggested_assignments.get(f"UART{uart_num}_TX", 17)
    rx_default = rec.suggested_assignments.get(f"UART{uart_num}_RX", 16)

    tx_gpio = IntPrompt.ask("TX pin", default=tx_default)
    rx_gpio = IntPrompt.ask("RX pin", default=rx_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  UART{uart_num}_TX = GPIO {tx_gpio}")
    console.print(f"  UART{uart_num}_RX = GPIO {rx_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        do_assign(f"UART{uart_num}_TX", tx_gpio, force=True)
        do_assign(f"UART{uart_num}_RX", rx_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0
