// src/command/handlers/StepperHandler.cpp
// Implementation of StepperHandler methods

#include "command/handlers/StepperHandler.h"
#include "motor/StepperManager.h"
#include "motor/MotionController.h"
#include "core/ServiceContext.h"
#include "core/Debug.h"

void StepperHandler::init(mara::ServiceContext& ctx) {
    stepper_ = ctx.stepper;
    motion_ = ctx.motion;
}

void StepperHandler::handleEnable(JsonVariantConst payload, CommandContext& ctx) {
    int motorId = payload["motor_id"] | 0;
    bool enable = payload["enable"] | true;

    DBG_PRINTF("[STEPPER] ENABLE motor=%d enable=%d\n", motorId, (int)enable);
    stepper_->setEnabled(motorId, enable);

    JsonDocument resp;
    resp["motor_id"] = motorId;
    resp["enable"] = enable;
    ctx.sendAck("CMD_STEPPER_ENABLE", true, resp);
}

void StepperHandler::handleMoveRel(JsonVariantConst payload, CommandContext& ctx) {
    if (!ctx.mode.canMove()) {
        ctx.sendError("CMD_STEPPER_MOVE_REL", "not_armed");
        return;
    }

    int motorId = payload["motor_id"] | 0;
    int steps = payload["steps"] | 0;
    float speed = payload["speed_steps_s"] | 1000.0f;

    DBG_PRINTF("[STEPPER] MOVE_REL motor=%d steps=%d speed=%.1f\n",
               motorId, steps, speed);

    const uint32_t now_ms = ctx.now_ms();
    ctx.mode.onMotionCommand(now_ms);

    // Store stepper intent (control task will consume and apply)
    if (ctx.intents) {
        ctx.intents->setStepperIntent(motorId, steps, speed, now_ms);
    } else {
        motion_->moveStepperRelative(motorId, steps, speed);  // Fallback
    }

    JsonDocument resp;
    resp["motor_id"] = motorId;
    resp["steps"] = steps;
    resp["speed_steps_s"] = speed;
    ctx.sendAck("CMD_STEPPER_MOVE_REL", true, resp);
}

void StepperHandler::handleStop(JsonVariantConst payload, CommandContext& ctx) {
    int motorId = payload["motor_id"] | 0;

    DBG_PRINTF("[STEPPER] STOP motor=%d\n", motorId);
    stepper_->stop(motorId);

    JsonDocument resp;
    resp["motor_id"] = motorId;
    ctx.sendAck("CMD_STEPPER_STOP", true, resp);
}
