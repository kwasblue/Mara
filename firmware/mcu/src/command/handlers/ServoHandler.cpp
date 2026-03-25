// src/command/handlers/ServoHandler.cpp
// Implementation of ServoHandler methods

#include "command/handlers/ServoHandler.h"
#include "config/PinConfig.h"
#include "core/Debug.h"

void ServoHandler::handleAttach(JsonVariantConst payload, CommandContext& ctx) {
    int servoId = payload["servo_id"] | 0;
    int minUs = payload["min_us"] | 1000;
    int maxUs = payload["max_us"] | 2000;
    int requestedChannel = payload["channel"] | -1;

    uint8_t pin = 0;
    bool ok = true;
    bool usedRequestedChannel = false;

    if (requestedChannel >= 0) {
        pin = static_cast<uint8_t>(requestedChannel);
        usedRequestedChannel = true;
    } else {
        switch (servoId) {
            case 0: pin = Pins::SERVO1_SIG; break;
            default:
                ok = false;
                break;
        }
    }

    if (ok) {
        DBG_PRINTF("[SERVO] ATTACH id=%d pin=%d min=%d max=%d requested=%d\n",
                   servoId, pin, minUs, maxUs, requestedChannel);
        servo_.attach(servoId, pin, minUs, maxUs);
    } else {
        DBG_PRINTF("[SERVO] ATTACH: unknown servoId=%d\n", servoId);
    }

    JsonDocument resp;
    resp["servo_id"] = servoId;
    resp["pin"] = pin;
    resp["channel"] = pin;
    resp["min_us"] = minUs;
    resp["max_us"] = maxUs;
    resp["used_requested_channel"] = usedRequestedChannel;
    if (!ok) {
        resp["error"] = "unknown_servo_id";
    }
    ctx.sendAck("CMD_SERVO_ATTACH", ok, resp);
}

void ServoHandler::handleDetach(JsonVariantConst payload, CommandContext& ctx) {
    int servoId = payload["servo_id"] | 0;

    DBG_PRINTF("[SERVO] DETACH id=%d\n", servoId);
    servo_.detach(servoId);

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

    DBG_PRINTF("[SERVO] SET_ANGLE id=%d angle=%.1f dur=%d\n",
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
            servo_.setAngle(servoId, angle);
        } else {
            motion_.setServoTarget(servoId, angle, durMs);
        }
    }

    JsonDocument resp;
    resp["servo_id"] = servoId;
    resp["angle_deg"] = angle;
    resp["duration_ms"] = durMs;
    ctx.sendAck("CMD_SERVO_SET_ANGLE", true, resp);
}
