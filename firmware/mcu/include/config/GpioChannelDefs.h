// AUTO-GENERATED FILE — DO NOT EDIT BY HAND
// Generated from GPIO_CHANNELS in platform_schema.py

#pragma once
#include <Arduino.h>
#include "config/PinConfig.h"

struct GpioChannelDef {
    int      channel;
    uint8_t  pin;
    uint8_t  mode;
    const char* name;
};

constexpr GpioChannelDef GPIO_CHANNEL_DEFS[] = {
    { 0, Pins::LED_STATUS, OUTPUT, "LED_STATUS" },
    { 1, Pins::ULTRA0_TRIG, OUTPUT, "ULTRASONIC_TRIG" },
    { 2, Pins::ULTRA0_ECHO, INPUT, "ULTRASONIC_ECHO" },
    { 3, Pins::MOTOR_LEFT_IN1, OUTPUT, "MOTOR_LEFT_IN1" },
    { 4, Pins::MOTOR_LEFT_IN2, OUTPUT, "MOTOR_LEFT_IN2" },
    { 5, Pins::STEPPER0_EN, OUTPUT, "STEPPER0_EN" },
    { 6, Pins::ENC0_A, INPUT, "ENC0_A" },
    { 7, Pins::ENC0_B, INPUT, "ENC0_B" },
};

constexpr size_t GPIO_CHANNEL_COUNT = sizeof(GPIO_CHANNEL_DEFS) / sizeof(GPIO_CHANNEL_DEFS[0]);
