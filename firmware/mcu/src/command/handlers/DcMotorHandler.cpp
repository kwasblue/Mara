// src/command/handlers/DcMotorHandler.cpp
// Implementation of DcMotorHandler methods

#include "command/handlers/DcMotorHandler.h"
#include "core/Debug.h"

void DcMotorHandler::handleSetSpeed(JsonVariantConst payload, CommandContext& ctx) {
    if (!ctx.mode.canMove()) {
        ctx.sendError("CMD_DC_SET_SPEED", "not_armed");
        return;
    }

    int motorId = payload["motor_id"] | 0;
    float speed = payload["speed"] | 0.0f;

    DBG_PRINTF("[DC] SET_SPEED motor=%d speed=%.3f\n", motorId, speed);

    const uint32_t now_ms = ctx.now_ms();
    ctx.mode.onMotionCommand(now_ms);

    bool ok = true;
    // Store DC motor intent (control task will consume and apply)
    if (ctx.intents) {
        ctx.intents->setDcMotorIntent(static_cast<uint8_t>(motorId), speed, now_ms);
    } else {
        ok = dc_.setSpeed(static_cast<uint8_t>(motorId), speed);  // Fallback
    }

    JsonDocument resp;
    resp["motor_id"] = motorId;
    resp["speed"] = speed;
    if (!ok) {
        resp["error"] = "set_speed_failed";
    }
    ctx.sendAck("CMD_DC_SET_SPEED", ok, resp);
}

void DcMotorHandler::handleStop(JsonVariantConst payload, CommandContext& ctx) {
    int motorId = payload["motor_id"] | 0;

    DBG_PRINTF("[DC] STOP motor=%d\n", motorId);
    dc_.stop(static_cast<uint8_t>(motorId));

    JsonDocument resp;
    resp["motor_id"] = motorId;
    ctx.sendAck("CMD_DC_STOP", true, resp);
}

void DcMotorHandler::handleVelPidEnable(JsonVariantConst payload, CommandContext& ctx) {
    int motorId = payload["motor_id"] | 0;
    bool enable = payload["enable"] | true;

    DBG_PRINTF("[DC] VEL_PID_ENABLE motor=%d enable=%d\n", motorId, (int)enable);
    bool ok = dc_.enableVelocityPid(static_cast<uint8_t>(motorId), enable);

    JsonDocument resp;
    resp["motor_id"] = motorId;
    resp["enable"] = enable;
    if (!ok) {
        resp["error"] = "enable_failed";
    }
    ctx.sendAck("CMD_DC_VEL_PID_ENABLE", ok, resp);
}

void DcMotorHandler::handleSetVelTarget(JsonVariantConst payload, CommandContext& ctx) {
    if (!ctx.mode.canMove()) {
        ctx.sendError("CMD_DC_SET_VEL_TARGET", "not_armed");
        return;
    }

    int motorId = payload["motor_id"] | 0;
    float omega = payload["omega"] | 0.0f;

    DBG_PRINTF("[DC] SET_VEL_TARGET motor=%d omega=%.3f\n", motorId, omega);

    ctx.mode.onMotionCommand(ctx.now_ms());
    bool ok = dc_.setVelocityTarget(static_cast<uint8_t>(motorId), omega);

    JsonDocument resp;
    resp["motor_id"] = motorId;
    resp["omega"] = omega;
    if (!ok) {
        resp["error"] = "set_target_failed";
    }
    ctx.sendAck("CMD_DC_SET_VEL_TARGET", ok, resp);
}

void DcMotorHandler::handleSetVelGains(JsonVariantConst payload, CommandContext& ctx) {
    int motorId = payload["motor_id"] | 0;
    float kp = payload["kp"] | 0.0f;
    float ki = payload["ki"] | 0.0f;
    float kd = payload["kd"] | 0.0f;

    DBG_PRINTF("[DC] SET_VEL_GAINS motor=%d kp=%.4f ki=%.4f kd=%.4f\n",
               motorId, kp, ki, kd);

    bool ok = dc_.setVelocityGains(static_cast<uint8_t>(motorId), kp, ki, kd);

    JsonDocument resp;
    resp["motor_id"] = motorId;
    resp["kp"] = kp;
    resp["ki"] = ki;
    resp["kd"] = kd;
    if (!ok) {
        resp["error"] = "set_gains_failed";
    }
    ctx.sendAck("CMD_DC_SET_VEL_GAINS", ok, resp);
}
