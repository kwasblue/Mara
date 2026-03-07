// src/command/handlers/SensorHandler.cpp
// Implementation of SensorHandler methods

#include "command/handlers/SensorHandler.h"
#include "config/PinConfig.h"
#include "core/Debug.h"

void SensorHandler::handleUltrasonicAttach(JsonVariantConst payload, CommandContext& ctx) {
    int sensorId = payload["sensor_id"] | 0;

    uint8_t trigPin = 0;
    uint8_t echoPin = 0;
    bool ok = true;

    switch (sensorId) {
        case 0:
            trigPin = Pins::ULTRA0_TRIG;
            echoPin = Pins::ULTRA0_ECHO;
            break;
        default:
            ok = false;
            break;
    }

    if (ok) {
        DBG_PRINTF("[SENSOR] ULTRASONIC_ATTACH id=%d trig=%d echo=%d\n",
                   sensorId, trigPin, echoPin);
        ok = ultrasonic_.attach(sensorId, trigPin, echoPin);
    } else {
        DBG_PRINTF("[SENSOR] ULTRASONIC_ATTACH: unknown sensorId=%d\n", sensorId);
    }

    JsonDocument resp;
    resp["sensor_id"] = sensorId;
    resp["trig_pin"] = trigPin;
    resp["echo_pin"] = echoPin;
    if (!ok) {
        resp["error"] = "attach_failed";
    }
    ctx.sendAck("CMD_ULTRASONIC_ATTACH", ok, resp);
}

void SensorHandler::handleUltrasonicRead(JsonVariantConst payload, CommandContext& ctx) {
    int sensorId = payload["sensor_id"] | 0;

    float distCm = ultrasonic_.readDistanceCm(sensorId);
    bool ok = (distCm >= 0.0f);

    DBG_PRINTF("[SENSOR] ULTRASONIC_READ id=%d dist=%.2f ok=%d\n",
               sensorId, distCm, (int)ok);

    JsonDocument resp;
    resp["sensor_id"] = sensorId;
    resp["distance_cm"] = ok ? distCm : -1.0f;
    if (!ok) {
        resp["error"] = "read_failed";
    }
    ctx.sendAck("CMD_ULTRASONIC_READ", ok, resp);
}

void SensorHandler::handleEncoderAttach(JsonVariantConst payload, CommandContext& ctx) {
    int encoderId = payload["encoder_id"] | 0;
    int pinA = payload["pin_a"] | Pins::ENC0_A;
    int pinB = payload["pin_b"] | Pins::ENC0_B;

    DBG_PRINTF("[SENSOR] ENCODER_ATTACH id=%d pinA=%d pinB=%d\n",
               encoderId, pinA, pinB);

    encoder_.attach(
        static_cast<uint8_t>(encoderId),
        static_cast<gpio_num_t>(pinA),
        static_cast<gpio_num_t>(pinB)
    );

    JsonDocument resp;
    resp["encoder_id"] = encoderId;
    resp["pin_a"] = pinA;
    resp["pin_b"] = pinB;
    ctx.sendAck("CMD_ENCODER_ATTACH", true, resp);
}

void SensorHandler::handleEncoderRead(JsonVariantConst payload, CommandContext& ctx) {
    int encoderId = payload["encoder_id"] | 0;

    int32_t ticks = encoder_.getCount(static_cast<uint8_t>(encoderId));

    DBG_PRINTF("[SENSOR] ENCODER_READ id=%d ticks=%ld\n", encoderId, (long)ticks);

    JsonDocument resp;
    resp["encoder_id"] = encoderId;
    resp["ticks"] = ticks;
    ctx.sendAck("CMD_ENCODER_READ", true, resp);
}

void SensorHandler::handleEncoderReset(JsonVariantConst payload, CommandContext& ctx) {
    int encoderId = payload["encoder_id"] | 0;

    DBG_PRINTF("[SENSOR] ENCODER_RESET id=%d\n", encoderId);
    encoder_.reset(static_cast<uint8_t>(encoderId));

    JsonDocument resp;
    resp["encoder_id"] = encoderId;
    ctx.sendAck("CMD_ENCODER_RESET", true, resp);
}
