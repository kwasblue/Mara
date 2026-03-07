// include/command/handlers/GpioHandler.h
// Handles GPIO, PWM, and LED commands

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "hw/GpioManager.h"
#include "hw/PwmManager.h"
#include "config/PinConfig.h"
#include "core/Debug.h"
#include <Arduino.h>

class GpioHandler : public ICommandHandler {
public:
    GpioHandler(GpioManager& gpio, PwmManager& pwm)
        : gpio_(gpio), pwm_(pwm) {}

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
    GpioManager& gpio_;
    PwmManager& pwm_;

    void handleGpioWrite(JsonVariantConst payload, CommandContext& ctx) {
        int ch = payload["channel"] | -1;
        int val = payload["value"] | 0;

        bool ok = gpio_.hasChannel(ch);
        if (ok) {
            gpio_.write(ch, val);
        }

        DBG_PRINTF("[GPIO] WRITE ch=%d val=%d ok=%d\n", ch, val, (int)ok);

        JsonDocument resp;
        resp["channel"] = ch;
        resp["value"] = val;
        if (!ok) {
            resp["error"] = "invalid_channel";
        }
        ctx.sendAck("CMD_GPIO_WRITE", ok, resp);
    }

    void handleGpioRead(JsonVariantConst payload, CommandContext& ctx) {
        int ch = payload["channel"] | -1;

        bool ok = gpio_.hasChannel(ch);
        int val = ok ? gpio_.read(ch) : -1;

        DBG_PRINTF("[GPIO] READ ch=%d val=%d ok=%d\n", ch, val, (int)ok);

        JsonDocument resp;
        resp["channel"] = ch;
        resp["value"] = val;
        if (!ok) {
            resp["error"] = "invalid_channel";
        }
        ctx.sendAck("CMD_GPIO_READ", ok, resp);
    }

    void handleGpioToggle(JsonVariantConst payload, CommandContext& ctx) {
        int ch = payload["channel"] | -1;

        bool ok = gpio_.hasChannel(ch);
        if (ok) {
            gpio_.toggle(ch);
        }

        DBG_PRINTF("[GPIO] TOGGLE ch=%d ok=%d\n", ch, (int)ok);

        JsonDocument resp;
        resp["channel"] = ch;
        if (!ok) {
            resp["error"] = "invalid_channel";
        }
        ctx.sendAck("CMD_GPIO_TOGGLE", ok, resp);
    }

    void handleGpioRegister(JsonVariantConst payload, CommandContext& ctx) {
        int ch = payload["channel"] | -1;
        int pin = payload["pin"] | -1;
        const char* modeStr = payload["mode"] | "output";

        int mode = OUTPUT;
        if (strcmp(modeStr, "input") == 0) {
            mode = INPUT;
        } else if (strcmp(modeStr, "input_pullup") == 0) {
            mode = INPUT_PULLUP;
        }

        bool ok = (ch >= 0 && pin >= 0);
        if (ok) {
            gpio_.registerChannel(ch, pin, mode);
        }

        DBG_PRINTF("[GPIO] REGISTER ch=%d pin=%d mode=%s ok=%d\n",
                   ch, pin, modeStr, (int)ok);

        JsonDocument resp;
        resp["channel"] = ch;
        resp["pin"] = pin;
        resp["mode"] = modeStr;
        if (!ok) {
            resp["error"] = "invalid_params";
        }
        ctx.sendAck("CMD_GPIO_REGISTER_CHANNEL", ok, resp);
    }

    void handlePwmSet(JsonVariantConst payload, CommandContext& ctx) {
        int channel = payload["channel"] | 0;
        float duty = payload["duty"] | 0.0f;
        float freq = payload["freq_hz"] | 0.0f;

        DBG_PRINTF("[GPIO] PWM_SET ch=%d duty=%.3f freq=%.1f\n", channel, duty, freq);

        pwm_.set(channel, duty, freq);

        JsonDocument resp;
        resp["channel"] = channel;
        resp["duty"] = duty;
        resp["freq_hz"] = freq;
        ctx.sendAck("CMD_PWM_SET", true, resp);
    }

    void handleLedOn(CommandContext& ctx) {
        DBG_PRINTLN("[GPIO] LED_ON");
        digitalWrite(Pins::LED_STATUS, HIGH);

        JsonDocument resp;
        resp["pin"] = Pins::LED_STATUS;
        resp["on"] = true;
        ctx.sendAck("CMD_LED_ON", true, resp);
    }

    void handleLedOff(CommandContext& ctx) {
        DBG_PRINTLN("[GPIO] LED_OFF");
        digitalWrite(Pins::LED_STATUS, LOW);

        JsonDocument resp;
        resp["pin"] = Pins::LED_STATUS;
        resp["on"] = false;
        ctx.sendAck("CMD_LED_OFF", true, resp);
    }
};
