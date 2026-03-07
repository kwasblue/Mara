| Command       | Direction  | Payload                             | Description                    | Safety Gate             |
| ------------- | ---------- | ----------------------------------- | ------------------------------ | ----------------------- |
| `SET_MODE`    | host → mcu | `{ "mode": "IDLE\|ARMED\|ACTIVE" }` | Change robot mode              | Ignored if in `ESTOP`   |
| `SET_VEL`     | host → mcu | `{ "vx": float, "omega": float }`   | Set body velocity (diff drive) | `mode.canMove` & !ESTOP |
| `STOP`        | host → mcu | none                                | Soft stop motion               | Always allowed          |
| `ESTOP`       | host → mcu | none                                | Emergency stop, enter ESTOP    | Always allowed          |
| `CLEAR_ESTOP` | host → mcu | none                                | Clear ESTOP, go to IDLE        | Always allowed          |


| Command   | Direction  | Payload | Description         |
| --------- | ---------- | ------- | ------------------- |
| `LED_ON`  | host → mcu | none    | Turn status LED on  |
| `LED_OFF` | host → mcu | none    | Turn status LED off |


| Command                 | Payload                                                                 | Notes                               |
| ----------------------- | ----------------------------------------------------------------------- | -----------------------------|
| `GPIO_WRITE`            | `{ "channel": int, "value": 0\|1 }`                                     | Returns `GPIO_WRITE_ACK`     |
| `GPIO_READ`             | `{ "channel": int }`                                                    | Returns `GPIO_READ_ACK`      |
| `GPIO_TOGGLE`           | `{ "channel": int }`                                                    | Returns `GPIO_TOGGLE_ACK`    |
| `GPIO_REGISTER_CHANNEL` | `{ "channel": int, "pin": int, "mode": "output\|input\|input_pullup" }` | Returns `GPIO_REGISTER_CHANNEL_ACK`|


| Command   | Payload                                                |
| --------- | ------------------------------------------------------ |
| `PWM_SET` | `{ "channel": int, "duty": float, "freq_hz": float? }` |


| Command           | Payload                                                        | Routed To                          |
| ----------------- | -------------------------------------------------------------- | ---------------------------------- |
| `SERVO_ATTACH`    | `{ "servo_id": int, "min_us": int, "max_us": int }`            | `ServoManager::attach`             |
| `SERVO_DETACH`    | `{ "servo_id": int }`                                          | `ServoManager::detach`             |
| `SERVO_SET_ANGLE` | `{ "servo_id": int, "angle_deg": float, "duration_ms": int? }` | `MotionController::setServoTarget` |


| Command            | Payload                                                     |
| ------------------ | ----------------------------------------------------------- |
| `STEPPER_MOVE_REL` | `{ "motor_id": int, "steps": int, "speed_steps_s": float }` |
| `STEPPER_STOP`     | `{ "motor_id": int }`                                       |


| Command         | Payload                                        | ACK             |
| --------------- | ---------------------------------------------- | --------------- |
| `SET_LOG_LEVEL` | `{ "level": "debug\|info\|warn\|error\|off" }` | `LOG_LEVEL_ACK` |
