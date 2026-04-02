// include/command/handlers/SensorHandler.h
// Handles sensor commands: ultrasonic, encoder

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"

// Forward declarations
class UltrasonicManager;
class EncoderManager;
class ImuManager;

class SensorHandler : public ICommandHandler {
public:
    SensorHandler() = default;

    void init(mara::ServiceContext& ctx) override;

    const char* name() const override { return "SensorHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::IMU_READ:
            case CmdType::I2C_SCAN:
            case CmdType::ULTRASONIC_ATTACH:
            case CmdType::ULTRASONIC_READ:
            case CmdType::ULTRASONIC_DETACH:
            case CmdType::ENCODER_ATTACH:
            case CmdType::ENCODER_READ:
            case CmdType::ENCODER_RESET:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::IMU_READ:          handleImuRead(ctx);                    break;
            case CmdType::I2C_SCAN:          handleI2cScan(ctx);                    break;
            case CmdType::ULTRASONIC_ATTACH: handleUltrasonicAttach(payload, ctx); break;
            case CmdType::ULTRASONIC_READ:   handleUltrasonicRead(payload, ctx);   break;
            case CmdType::ULTRASONIC_DETACH: handleUltrasonicDetach(payload, ctx); break;
            case CmdType::ENCODER_ATTACH:    handleEncoderAttach(payload, ctx);    break;
            case CmdType::ENCODER_READ:      handleEncoderRead(payload, ctx);      break;
            case CmdType::ENCODER_RESET:     handleEncoderReset(payload, ctx);     break;
            default: break;
        }
    }

private:
    UltrasonicManager* ultrasonic_ = nullptr;
    EncoderManager* encoder_ = nullptr;
    ImuManager* imu_ = nullptr;

    // Implemented in SensorHandler.cpp
    void handleImuRead(CommandContext& ctx);
    void handleI2cScan(CommandContext& ctx);
    void handleUltrasonicAttach(JsonVariantConst payload, CommandContext& ctx);
    void handleUltrasonicRead(JsonVariantConst payload, CommandContext& ctx);
    void handleUltrasonicDetach(JsonVariantConst payload, CommandContext& ctx);
    void handleEncoderAttach(JsonVariantConst payload, CommandContext& ctx);
    void handleEncoderRead(JsonVariantConst payload, CommandContext& ctx);
    void handleEncoderReset(JsonVariantConst payload, CommandContext& ctx);
};
