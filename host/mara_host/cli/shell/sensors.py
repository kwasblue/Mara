# mara_host/cli/commands/run/shell/commands/sensors.py
"""Sensor commands: encoder, imu, ultrasonic."""

from .registry import command
from mara_host.cli.console import console, print_success, print_error, print_info


@command("encoder", "Encoder: encoder attach/read/reset/detach ...", group="Sensors")
async def cmd_encoder(shell, args: list[str]) -> None:
    """Encoder commands."""
    if not args:
        console.print("Usage:")
        console.print("  encoder attach <id> <pin_a> <pin_b> [ppr]  Attach encoder")
        console.print("  encoder read <id>                          Read encoder")
        console.print("  encoder reset <id>                         Reset count")
        console.print("  encoder detach <id>                        Detach encoder")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()
    if action == "attach" and len(args) >= 4:
        encoder_id = int(args[1])
        pin_a = int(args[2])
        pin_b = int(args[3])
        ppr = int(args[4]) if len(args) > 4 else 20
        await shell.client.send_reliable("CMD_ENCODER_ATTACH", {"encoder_id": encoder_id, "pin_a": pin_a, "pin_b": pin_b, "ppr": ppr})
        print_success(f"Encoder {encoder_id} attached to pins {pin_a}/{pin_b}")
    elif action == "read" and len(args) >= 2:
        encoder_id = int(args[1])
        await shell.client.send_reliable("CMD_ENCODER_READ", {"encoder_id": encoder_id})
        print_info(f"Encoder {encoder_id} read requested (check events)")
    elif action == "reset" and len(args) >= 2:
        encoder_id = int(args[1])
        await shell.client.send_reliable("CMD_ENCODER_RESET", {"encoder_id": encoder_id})
        print_success(f"Encoder {encoder_id} reset")
    elif action == "detach" and len(args) >= 2:
        encoder_id = int(args[1])
        await shell.client.send_reliable("CMD_ENCODER_DETACH", {"encoder_id": encoder_id})
        print_success(f"Encoder {encoder_id} detached")
    else:
        print_error(f"Unknown encoder action: {args}")


@command("imu", "IMU: imu read/calibrate/bias ...", group="Sensors")
async def cmd_imu(shell, args: list[str]) -> None:
    """IMU commands."""
    if not args:
        console.print("Usage:")
        console.print("  imu read                        Read IMU data")
        console.print("  imu calibrate [samples] [delay] Calibrate IMU")
        console.print("  imu bias <ax> <ay> <az> <gx> <gy> <gz>  Set bias")
        console.print("  imu attach <type>               Attach IMU (mpu6050, etc)")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()
    if action == "read":
        await shell.client.send_reliable("CMD_IMU_READ", {})
        print_info("IMU read requested (check events)")
    elif action == "calibrate":
        samples = int(args[1]) if len(args) > 1 else 100
        delay_ms = int(args[2]) if len(args) > 2 else 10
        await shell.client.send_reliable("CMD_IMU_CALIBRATE", {"samples": samples, "delay_ms": delay_ms})
        print_info(f"IMU calibration started ({samples} samples)")
    elif action == "bias" and len(args) >= 7:
        await shell.client.send_reliable("CMD_IMU_SET_BIAS", {
            "ax": float(args[1]), "ay": float(args[2]), "az": float(args[3]),
            "gx": float(args[4]), "gy": float(args[5]), "gz": float(args[6]),
        })
        print_success("IMU bias set")
    elif action == "attach" and len(args) >= 2:
        imu_type = args[1]
        await shell.client.send_reliable("CMD_IMU_ATTACH", {"type": imu_type})
        print_success(f"IMU {imu_type} attached")
    else:
        print_error(f"Unknown imu action: {args}")


@command("ultrasonic", "Ultrasonic: ultrasonic attach/read/detach ...", group="Sensors")
async def cmd_ultrasonic(shell, args: list[str]) -> None:
    """Ultrasonic sensor commands."""
    if not args:
        console.print("Usage:")
        console.print("  ultrasonic attach <id> <trig> <echo>  Attach sensor")
        console.print("  ultrasonic read <id>                  Read distance")
        console.print("  ultrasonic detach <id>                Detach sensor")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()
    if action == "attach" and len(args) >= 4:
        sensor_id = int(args[1])
        trig_pin = int(args[2])
        echo_pin = int(args[3])
        await shell.client.send_reliable("CMD_ULTRASONIC_ATTACH", {"sensor_id": sensor_id, "trig_pin": trig_pin, "echo_pin": echo_pin})
        print_success(f"Ultrasonic {sensor_id} attached (trig={trig_pin}, echo={echo_pin})")
    elif action == "read" and len(args) >= 2:
        sensor_id = int(args[1])
        await shell.client.send_reliable("CMD_ULTRASONIC_READ", {"sensor_id": sensor_id})
        print_info(f"Ultrasonic {sensor_id} read requested (check events)")
    elif action == "detach" and len(args) >= 2:
        sensor_id = int(args[1])
        await shell.client.send_reliable("CMD_ULTRASONIC_DETACH", {"sensor_id": sensor_id})
        print_success(f"Ultrasonic {sensor_id} detached")
    else:
        print_error(f"Unknown ultrasonic action: {args}")
