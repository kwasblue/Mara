// include/command/handlers/GpioHandler.h
// Handles GPIO, PWM, and LED commands

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"

// Forward declarations
class GpioManager;
class PwmManager;

class GpioHandler : public ICommandHandler {
public:
    GpioHandler() = default;

    void init(mara::ServiceContext& ctx) override;

    const char* name() const override { return "GpioHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::GPIO_WRITE:
            case CmdType::GPIO_READ:
            case CmdType::GPIO_TOGGLE:
            case CmdType::GPIO_REGISTER_CHANNEL:
            case CmdType::PWM_SET:
            case CmdType::LED_ON:
            case CmdType::LED_OFF:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::GPIO_WRITE:            handleGpioWrite(payload, ctx);    break;
            case CmdType::GPIO_READ:             handleGpioRead(payload, ctx);     break;
            case CmdType::GPIO_TOGGLE:           handleGpioToggle(payload, ctx);   break;
            case CmdType::GPIO_REGISTER_CHANNEL: handleGpioRegister(payload, ctx); break;
            case CmdType::PWM_SET:               handlePwmSet(payload, ctx);       break;
            case CmdType::LED_ON:                handleLedOn(ctx);                 break;
            case CmdType::LED_OFF:               handleLedOff(ctx);                break;
            default: break;
        }
    }

private:
    GpioManager* gpio_ = nullptr;
    PwmManager* pwm_ = nullptr;

    // Implemented in GpioHandler.cpp
    void handleGpioWrite(JsonVariantConst payload, CommandContext& ctx);
    void handleGpioRead(JsonVariantConst payload, CommandContext& ctx);
    void handleGpioToggle(JsonVariantConst payload, CommandContext& ctx);
    void handleGpioRegister(JsonVariantConst payload, CommandContext& ctx);
    void handlePwmSet(JsonVariantConst payload, CommandContext& ctx);
    void handleLedOn(CommandContext& ctx);
    void handleLedOff(CommandContext& ctx);
};
