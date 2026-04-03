// src/command/handlers/ServoHandler.cpp
// Implementation of ServoHandler methods

#include "command/handlers/ServoHandler.h"
#include "motor/ServoManager.h"
#include "motor/MotionController.h"
#include "core/ServiceContext.h"
#include "module/LoggingModule.h"
#include "config/PinConfig.h"
#include "core/Debug.h"
#include <cmath>
#include <cstring>

void ServoHandler::init(mara::ServiceContext& ctx) {
    servo_ = ctx.servo;
    motion_ = ctx.motion;
}

void ServoHandler::handleAttach(JsonVariantConst payload, CommandContext& ctx) {
    // ESP32 GPIO range: 0-39 (with some pins reserved/input-only, but HAL handles that)
    static constexpr int MAX_GPIO_PIN = 39;

    int servoId = payload["servo_id"] | 0;
    int minUs = payload["min_us"] | 1000;
    int maxUs = payload["max_us"] | 2000;
    int requestedChannel = payload["channel"] | -1;

    uint8_t pin = 0;
    bool ok = true;
    bool usedRequestedChannel = false;
    const char* error = nullptr;

    if (requestedChannel >= 0) {
        // Validate GPIO pin range when channel is explicitly specified
        if (requestedChannel > MAX_GPIO_PIN) {
            ok = false;
            error = "invalid_gpio_pin";
            MARA_LOG_WARN("servo", "ATTACH: invalid GPIO pin=%d (max=%d)", requestedChannel, MAX_GPIO_PIN);
        } else {
            pin = static_cast<uint8_t>(requestedChannel);
            usedRequestedChannel = true;
        }
    } else {
        // Use default pin mapping for known servo IDs
        switch (servoId) {
            case 0: pin = Pins::SERVO1_SIG; break;
            default:
                ok = false;
                error = "no_default_pin_for_servo_id";
                break;
        }
    }

    if (ok) {
        MARA_LOG_DEBUG("servo", "ATTACH id=%d pin=%d min=%d max=%d requested=%d",
                       servoId, pin, minUs, maxUs, requestedChannel);
        // Note: ServoManager::attach validates servoId internally
        servo_->attach(servoId, pin, minUs, maxUs);
    }

    JsonDocument resp;
    resp["servo_id"] = servoId;
    resp["pin"] = pin;
    resp["channel"] = pin;
    resp["min_us"] = minUs;
    resp["max_us"] = maxUs;
    resp["used_requested_channel"] = usedRequestedChannel;
    if (!ok && error) {
        resp["error"] = error;
    }
    ctx.sendAck("CMD_SERVO_ATTACH", ok, resp);
}

void ServoHandler::handleDetach(JsonVariantConst payload, CommandContext& ctx) {
    int servoId = payload["servo_id"] | 0;

    MARA_LOG_DEBUG("servo", "DETACH id=%d", servoId);
    servo_->detach(servoId);

    JsonDocument resp;
    resp["servo_id"] = servoId;
    ctx.sendAck("CMD_SERVO_DETACH", true, resp);
}

void ServoHandler::handleSetAngle(JsonVariantConst payload, CommandContext& ctx) {
    if (!ctx.mode.canMove()) {
        ctx.sendError("CMD_SERVO_SET_ANGLE", "not_armed");
        return;
    }

    int servoId = payload["servo_id"] | 0;
    float angle = payload["angle_deg"] | 0.0f;
    int durMs = payload["duration_ms"] | 0;

    MARA_LOG_DEBUG("servo", "SET_ANGLE id=%d angle=%.1f dur=%d",
                   servoId, angle, durMs);

    const uint32_t now_ms = ctx.now_ms();
    ctx.mode.onMotionCommand(now_ms);

    // Store servo intent (control task will consume and apply)
    if (ctx.intents) {
        ctx.intents->setServoIntent(static_cast<uint8_t>(servoId), angle,
                                     static_cast<uint32_t>(durMs > 0 ? durMs : 0), now_ms);
    } else {
        // Fallback for non-intent path
        if (durMs <= 0) {
            servo_->setAngle(servoId, angle);
        } else {
            motion_->setServoTarget(servoId, angle, durMs);
        }
    }

    JsonDocument resp;
    resp["servo_id"] = servoId;
    resp["angle_deg"] = angle;
    resp["duration_ms"] = durMs;
    ctx.sendAck("CMD_SERVO_SET_ANGLE", true, resp);
}


namespace {

bool isFiniteNumber(float value) {
    return !std::isnan(value) && !std::isinf(value);
}

bool hasMotorSetFor(const mara::CompositeIntent& batch, uint8_t motorId) {
    for (uint8_t i = 0; i < batch.dc_motor_set_count; ++i) {
        if (batch.dc_motor_sets[i].motor_id == motorId) return true;
    }
    return false;
}

bool hasMotorStopFor(const mara::CompositeIntent& batch, uint8_t motorId) {
    for (uint8_t i = 0; i < batch.dc_motor_stop_count; ++i) {
        if (batch.dc_motor_stops[i].motor_id == motorId) return true;
    }
    return false;
}

bool hasStepperMoveFor(const mara::CompositeIntent& batch, uint8_t motorId) {
    for (uint8_t i = 0; i < batch.stepper_move_count; ++i) {
        if (batch.stepper_moves[i].motor_id == motorId) return true;
    }
    return false;
}

bool hasStepperStopFor(const mara::CompositeIntent& batch, uint8_t motorId) {
    for (uint8_t i = 0; i < batch.stepper_stop_count; ++i) {
        if (batch.stepper_stops[i].motor_id == motorId) return true;
    }
    return false;
}

void sendBatchError(CommandContext& ctx, const char* error, const char* cmd = nullptr, int index = -1) {
    JsonDocument resp;
    resp["error"] = error;
    if (cmd && cmd[0] != '\0') resp["cmd"] = cmd;
    if (index >= 0) resp["index"] = index;
    ctx.sendAck("CMD_BATCH_APPLY", false, resp);
}

bool handleBatchGpioWrite(JsonObjectConst args, mara::CompositeIntent& batch, CommandContext& ctx, const char* cmd, int index) {
    int channel = args["channel"] | -1;
    int value = args["value"] | -1;
    if (channel < 0) {
        sendBatchError(ctx, "invalid_channel", cmd, index);
        return false;
    }
    if (value != 0 && value != 1) {
        sendBatchError(ctx, "invalid_value", cmd, index);
        return false;
    }
    if (batch.gpio_count >= mara::CompositeIntent::MAX_GPIO_WRITES) {
        sendBatchError(ctx, "too_many_gpio_actions", cmd, index);
        return false;
    }
    auto& gpio = batch.gpio_writes[batch.gpio_count++];
    gpio.channel = static_cast<uint8_t>(channel);
    gpio.value = value != 0;
    return true;
}

bool handleBatchServoSet(JsonObjectConst args, mara::CompositeIntent& batch, CommandContext& ctx, const char* cmd, int index) {
    int servoId = args["servo_id"] | -1;
    float angle = args["angle_deg"] | 0.0f;
    int durMs = args["duration_ms"] | 0;
    if (servoId < 0) {
        sendBatchError(ctx, "invalid_servo_id", cmd, index);
        return false;
    }
    if (!isFiniteNumber(angle) || angle < 0.0f || angle > 180.0f) {
        sendBatchError(ctx, "invalid_angle_deg", cmd, index);
        return false;
    }
    if (durMs < 0) {
        sendBatchError(ctx, "invalid_duration_ms", cmd, index);
        return false;
    }
    if (batch.servo_count >= mara::CompositeIntent::MAX_SERVO_ACTIONS) {
        sendBatchError(ctx, "too_many_servo_actions", cmd, index);
        return false;
    }
    auto& servo = batch.servo_sets[batch.servo_count++];
    servo.servo_id = static_cast<uint8_t>(servoId);
    servo.angle_deg = angle;
    servo.duration_ms = static_cast<uint32_t>(durMs);
    return true;
}

bool handleBatchPwmSet(JsonObjectConst args, mara::CompositeIntent& batch, CommandContext& ctx, const char* cmd, int index) {
    int channel = args["channel"] | -1;
    float duty = args["duty"] | -1.0f;
    float freq = args["freq_hz"] | 0.0f;
    if (channel < 0) {
        sendBatchError(ctx, "invalid_channel", cmd, index);
        return false;
    }
    if (!isFiniteNumber(duty) || duty < 0.0f || duty > 1.0f) {
        sendBatchError(ctx, "invalid_duty", cmd, index);
        return false;
    }
    if (!isFiniteNumber(freq) || freq < 0.0f) {
        sendBatchError(ctx, "invalid_freq_hz", cmd, index);
        return false;
    }
    if (batch.pwm_count >= mara::CompositeIntent::MAX_PWM_ACTIONS) {
        sendBatchError(ctx, "too_many_pwm_actions", cmd, index);
        return false;
    }
    auto& pwm = batch.pwm_sets[batch.pwm_count++];
    pwm.channel = static_cast<uint8_t>(channel);
    pwm.duty = duty;
    pwm.freq_hz = freq;
    return true;
}

bool handleBatchDcSetSpeed(JsonObjectConst args, mara::CompositeIntent& batch, CommandContext& ctx, const char* cmd, int index) {
    int motorId = args["motor_id"] | -1;
    float speed = args["speed"] | 0.0f;
    if (motorId < 0) {
        sendBatchError(ctx, "invalid_motor_id", cmd, index);
        return false;
    }
    if (!isFiniteNumber(speed) || speed < -1.0f || speed > 1.0f) {
        sendBatchError(ctx, "invalid_speed", cmd, index);
        return false;
    }
    uint8_t motor = static_cast<uint8_t>(motorId);
    if (hasMotorSetFor(batch, motor) || hasMotorStopFor(batch, motor)) {
        sendBatchError(ctx, "conflicting_motor_action", cmd, index);
        return false;
    }
    if (batch.dc_motor_set_count >= mara::CompositeIntent::MAX_DC_MOTOR_SET_ACTIONS) {
        sendBatchError(ctx, "too_many_motor_set_actions", cmd, index);
        return false;
    }
    auto& dc = batch.dc_motor_sets[batch.dc_motor_set_count++];
    dc.motor_id = motor;
    dc.speed = speed;
    return true;
}

bool handleBatchDcStop(JsonObjectConst args, mara::CompositeIntent& batch, CommandContext& ctx, const char* cmd, int index) {
    int motorId = args["motor_id"] | -1;
    if (motorId < 0) {
        sendBatchError(ctx, "invalid_motor_id", cmd, index);
        return false;
    }
    uint8_t motor = static_cast<uint8_t>(motorId);
    if (hasMotorSetFor(batch, motor) || hasMotorStopFor(batch, motor)) {
        sendBatchError(ctx, "conflicting_motor_action", cmd, index);
        return false;
    }
    if (batch.dc_motor_stop_count >= mara::CompositeIntent::MAX_DC_MOTOR_STOP_ACTIONS) {
        sendBatchError(ctx, "too_many_motor_stop_actions", cmd, index);
        return false;
    }
    auto& dc = batch.dc_motor_stops[batch.dc_motor_stop_count++];
    dc.motor_id = motor;
    return true;
}

bool handleBatchStepperMove(JsonObjectConst args, mara::CompositeIntent& batch, CommandContext& ctx, const char* cmd, int index) {
    int motorId = args["motor_id"] | -1;
    int steps = args["steps"] | 0;
    float speed = args["speed_steps_s"] | 1000.0f;
    if (motorId < 0) {
        sendBatchError(ctx, "invalid_motor_id", cmd, index);
        return false;
    }
    if (steps == 0) {
        sendBatchError(ctx, "invalid_steps", cmd, index);
        return false;
    }
    if (!isFiniteNumber(speed) || speed <= 0.0f) {
        sendBatchError(ctx, "invalid_speed_steps_s", cmd, index);
        return false;
    }
    uint8_t motor = static_cast<uint8_t>(motorId);
    if (hasStepperMoveFor(batch, motor) || hasStepperStopFor(batch, motor)) {
        sendBatchError(ctx, "conflicting_stepper_action", cmd, index);
        return false;
    }
    if (batch.stepper_move_count >= mara::CompositeIntent::MAX_STEPPER_MOVE_ACTIONS) {
        sendBatchError(ctx, "too_many_stepper_move_actions", cmd, index);
        return false;
    }
    auto& stepper = batch.stepper_moves[batch.stepper_move_count++];
    stepper.motor_id = motor;
    stepper.steps = steps;
    stepper.speed_steps_s = speed;
    return true;
}

bool handleBatchStepperStop(JsonObjectConst args, mara::CompositeIntent& batch, CommandContext& ctx, const char* cmd, int index) {
    int motorId = args["motor_id"] | -1;
    if (motorId < 0) {
        sendBatchError(ctx, "invalid_motor_id", cmd, index);
        return false;
    }
    uint8_t motor = static_cast<uint8_t>(motorId);
    if (hasStepperMoveFor(batch, motor) || hasStepperStopFor(batch, motor)) {
        sendBatchError(ctx, "conflicting_stepper_action", cmd, index);
        return false;
    }
    if (batch.stepper_stop_count >= mara::CompositeIntent::MAX_STEPPER_STOP_ACTIONS) {
        sendBatchError(ctx, "too_many_stepper_stop_actions", cmd, index);
        return false;
    }
    auto& stepper = batch.stepper_stops[batch.stepper_stop_count++];
    stepper.motor_id = motor;
    return true;
}

}

void ServoHandler::handleBatchApply(JsonVariantConst payload, CommandContext& ctx) {
    if (!ctx.mode.canMove()) {
        ctx.sendError("CMD_BATCH_APPLY", "not_armed");
        return;
    }
    if (!ctx.intents) {
        ctx.sendError("CMD_BATCH_APPLY", "intents_unavailable");
        return;
    }

    JsonArrayConst actions = payload["actions"].as<JsonArrayConst>();
    if (actions.isNull() || actions.size() == 0) {
        sendBatchError(ctx, "actions_required");
        return;
    }

    mara::CompositeIntent batch{};
    const uint32_t now_ms = ctx.now_ms();
    batch.timestamp_ms = now_ms;

    int index = 0;
    for (JsonObjectConst action : actions) {
        const char* cmd = action["cmd"] | "";
        JsonObjectConst args = action["args"].as<JsonObjectConst>();

        if (cmd[0] == '\0') {
            sendBatchError(ctx, "missing_cmd", nullptr, index);
            return;
        }
        if (args.isNull()) {
            sendBatchError(ctx, "invalid_args", cmd, index);
            return;
        }

        bool ok = false;
        if (strcmp(cmd, "CMD_GPIO_WRITE") == 0) {
            ok = handleBatchGpioWrite(args, batch, ctx, cmd, index);
        } else if (strcmp(cmd, "CMD_SERVO_SET_ANGLE") == 0) {
            ok = handleBatchServoSet(args, batch, ctx, cmd, index);
        } else if (strcmp(cmd, "CMD_PWM_SET") == 0) {
            ok = handleBatchPwmSet(args, batch, ctx, cmd, index);
        } else if (strcmp(cmd, "CMD_DC_SET_SPEED") == 0) {
            ok = handleBatchDcSetSpeed(args, batch, ctx, cmd, index);
        } else if (strcmp(cmd, "CMD_DC_STOP") == 0) {
            ok = handleBatchDcStop(args, batch, ctx, cmd, index);
        } else if (strcmp(cmd, "CMD_STEPPER_MOVE_REL") == 0) {
            ok = handleBatchStepperMove(args, batch, ctx, cmd, index);
        } else if (strcmp(cmd, "CMD_STEPPER_STOP") == 0) {
            ok = handleBatchStepperStop(args, batch, ctx, cmd, index);
        } else {
            sendBatchError(ctx, "unsupported_batch_command", cmd, index);
            return;
        }

        if (!ok) {
            return;
        }
        ++index;
    }

    // Set intent first, then update motion heartbeat
    // (heartbeat should only be updated after successful dispatch)
    ctx.intents->setCompositeIntent(batch);
    ctx.mode.onMotionCommand(now_ms);

    JsonDocument resp;
    resp["action_count"] = actions.size();
    resp["gpio_count"] = batch.gpio_count;
    resp["servo_count"] = batch.servo_count;
    resp["pwm_count"] = batch.pwm_count;
    resp["motor_set_count"] = batch.dc_motor_set_count;
    resp["motor_stop_count"] = batch.dc_motor_stop_count;
    resp["stepper_move_count"] = batch.stepper_move_count;
    resp["stepper_stop_count"] = batch.stepper_stop_count;
    ctx.sendAck("CMD_BATCH_APPLY", true, resp);
}
