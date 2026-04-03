// src/command/handlers/GpioHandler.cpp
// Implementation of GpioHandler methods

#include "command/handlers/GpioHandler.h"
#include "hw/GpioManager.h"
#include "hw/PwmManager.h"
#include "core/ServiceContext.h"
#include "config/PinConfig.h"
#include "core/Debug.h"
#include <Arduino.h>
#include <cstring>

void GpioHandler::init(mara::ServiceContext& ctx) {
    gpio_ = ctx.gpio;
    pwm_ = ctx.pwm;
}

void GpioHandler::handleGpioWrite(JsonVariantConst payload, CommandContext& ctx) {
    int ch = payload["channel"] | -1;
    int rawVal = payload["value"] | 0;
    // Normalize to 0 or 1 for safety (accepts any truthy/falsy value)
    int val = (rawVal != 0) ? 1 : 0;

    bool ok = gpio_->hasChannel(ch);
    if (ok) {
        gpio_->write(ch, val);
    }

    DBG_PRINTF("[GPIO] WRITE ch=%d val=%d (raw=%d) ok=%d\n", ch, val, rawVal, (int)ok);

    JsonDocument resp;
    resp["channel"] = ch;
    resp["value"] = val;
    if (!ok) {
        resp["error"] = "invalid_channel";
    }
    ctx.sendAck("CMD_GPIO_WRITE", ok, resp);
}

void GpioHandler::handleGpioRead(JsonVariantConst payload, CommandContext& ctx) {
    int ch = payload["channel"] | -1;

    bool ok = gpio_->hasChannel(ch);
    int val = ok ? gpio_->read(ch) : -1;

    DBG_PRINTF("[GPIO] READ ch=%d val=%d ok=%d\n", ch, val, (int)ok);

    JsonDocument resp;
    resp["channel"] = ch;
    resp["value"] = val;
    if (!ok) {
        resp["error"] = "invalid_channel";
    }
    ctx.sendAck("CMD_GPIO_READ", ok, resp);
}

void GpioHandler::handleGpioToggle(JsonVariantConst payload, CommandContext& ctx) {
    int ch = payload["channel"] | -1;

    bool ok = gpio_->hasChannel(ch);
    if (ok) {
        gpio_->toggle(ch);
    }

    DBG_PRINTF("[GPIO] TOGGLE ch=%d ok=%d\n", ch, (int)ok);

    JsonDocument resp;
    resp["channel"] = ch;
    if (!ok) {
        resp["error"] = "invalid_channel";
    }
    ctx.sendAck("CMD_GPIO_TOGGLE", ok, resp);
}

void GpioHandler::handleGpioRegister(JsonVariantConst payload, CommandContext& ctx) {
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
        gpio_->registerChannel(ch, pin, mode);
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

void GpioHandler::handlePwmSet(JsonVariantConst payload, CommandContext& ctx) {
    int channel = payload["channel"] | 0;
    float duty = payload["duty"] | 0.0f;
    float freq = payload["freq_hz"] | 0.0f;

    DBG_PRINTF("[GPIO] PWM_SET ch=%d duty=%.3f freq=%.1f\n", channel, duty, freq);

    // Check if channel is registered before setting
    bool ok = pwm_->hasChannel(channel);
    if (ok) {
        pwm_->set(channel, duty, freq);
    }

    JsonDocument resp;
    resp["channel"] = channel;
    resp["duty"] = duty;
    resp["freq_hz"] = freq;
    if (!ok) {
        resp["error"] = "channel_not_registered";
    }
    ctx.sendAck("CMD_PWM_SET", ok, resp);
}

void GpioHandler::handleLedOn(CommandContext& ctx) {
    DBG_PRINTLN("[GPIO] LED_ON");
    digitalWrite(Pins::LED_STATUS, HIGH);

    JsonDocument resp;
    resp["pin"] = Pins::LED_STATUS;
    resp["on"] = true;
    ctx.sendAck("CMD_LED_ON", true, resp);
}

void GpioHandler::handleLedOff(CommandContext& ctx) {
    DBG_PRINTLN("[GPIO] LED_OFF");
    digitalWrite(Pins::LED_STATUS, LOW);

    JsonDocument resp;
    resp["pin"] = Pins::LED_STATUS;
    resp["on"] = false;
    ctx.sendAck("CMD_LED_OFF", true, resp);
}
