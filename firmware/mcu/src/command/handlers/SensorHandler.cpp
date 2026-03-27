// src/command/handlers/SensorHandler.cpp
// Implementation of SensorHandler methods

#include "command/handlers/SensorHandler.h"
#include "config/PinConfig.h"
#include "core/Debug.h"

namespace {
constexpr uint8_t REG_WHO_AM_I = 0x75;

const char* classifyI2cDevice(uint8_t address, uint8_t whoAmI, bool whoOk, bool imuOnline, uint8_t imuAddr) {
    if (imuOnline && address == imuAddr) {
        return "imu";
    }
    if (whoOk) {
        switch (whoAmI) {
            case 0x12:
            case 0x68:
            case 0x70:
            case 0x71:
            case 0x73:
                return "imu_candidate";
            default:
                break;
        }
    }
    if (address == 0x29) {
        return "vl53l0x_candidate";
    }
    return "unknown";
}
}

void SensorHandler::handleImuRead(CommandContext& ctx) {
    JsonDocument resp;
    const bool online = imu_.isOnline();
    resp["online"] = online;

    if (!online) {
        resp["error"] = "offline";
        ctx.sendAck("CMD_IMU_READ", false, resp);
        return;
    }

    ImuManager::Sample sample;
    const bool ok = imu_.readSample(sample);
    resp["ax_g"] = ok ? sample.ax_g : 0.0f;
    resp["ay_g"] = ok ? sample.ay_g : 0.0f;
    resp["az_g"] = ok ? sample.az_g : 0.0f;
    resp["gx_dps"] = ok ? sample.gx_dps : 0.0f;
    resp["gy_dps"] = ok ? sample.gy_dps : 0.0f;
    resp["gz_dps"] = ok ? sample.gz_dps : 0.0f;
    resp["temp_c"] = ok ? sample.temp_c : 0.0f;
    if (!ok) {
        resp["error"] = "read_failed";
    }

    ctx.sendAck("CMD_IMU_READ", ok, resp);
}

void SensorHandler::handleI2cScan(CommandContext& ctx) {
    JsonDocument resp;
    auto* bus = imu_.hal();
    if (!bus) {
        resp["error"] = "i2c_unavailable";
        ctx.sendAck("CMD_I2C_SCAN", false, resp);
        return;
    }

    JsonArray found = resp["addresses"].to<JsonArray>();
    JsonArray devices = resp["devices"].to<JsonArray>();
    bool imuOnline = imu_.isOnline();
    uint8_t imuAddr = imu_.address();

    for (uint8_t address = 0x08; address <= 0x77; ++address) {
        if (!bus->devicePresent(address)) {
            continue;
        }

        char hexAddr[5];
        snprintf(hexAddr, sizeof(hexAddr), "0x%02X", address);
        found.add(hexAddr);

        JsonObject dev = devices.add<JsonObject>();
        dev["address"] = address;
        dev["address_hex"] = hexAddr;

        uint8_t whoAmI = 0;
        bool whoOk = (bus->readReg(address, REG_WHO_AM_I, &whoAmI) == hal::I2cResult::Ok);
        if (whoOk) {
            char whoHex[5];
            snprintf(whoHex, sizeof(whoHex), "0x%02X", whoAmI);
            dev["who_am_i"] = whoHex;
        }
        dev["kind"] = classifyI2cDevice(address, whoAmI, whoOk, imuOnline, imuAddr);
    }

    resp["count"] = found.size();
    resp["imu_online"] = imuOnline;
    if (imuOnline) {
        char imuHex[5];
        snprintf(imuHex, sizeof(imuHex), "0x%02X", imuAddr);
        resp["imu_address"] = imuHex;
    }
    ctx.sendAck("CMD_I2C_SCAN", true, resp);
}

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
