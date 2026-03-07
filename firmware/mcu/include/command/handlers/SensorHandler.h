// include/command/handlers/SensorHandler.h
// Handles sensor commands: ultrasonic, encoder

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "sensor/UltrasonicManager.h"
#include "sensor/EncoderManager.h"

class SensorHandler : public ICommandHandler {
public:
    SensorHandler(UltrasonicManager& ultrasonic, EncoderManager& encoder)
        : ultrasonic_(ultrasonic), encoder_(encoder) {}

    const char* name() const override { return "SensorHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::ULTRASONIC_ATTACH:
            case CmdType::ULTRASONIC_READ:
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
            case CmdType::ULTRASONIC_ATTACH: handleUltrasonicAttach(payload, ctx); break;
            case CmdType::ULTRASONIC_READ:   handleUltrasonicRead(payload, ctx);   break;
            case CmdType::ENCODER_ATTACH:    handleEncoderAttach(payload, ctx);    break;
            case CmdType::ENCODER_READ:      handleEncoderRead(payload, ctx);      break;
            case CmdType::ENCODER_RESET:     handleEncoderReset(payload, ctx);     break;
            default: break;
        }
    }

private:
    UltrasonicManager& ultrasonic_;
    EncoderManager& encoder_;

    // Implemented in SensorHandler.cpp
    void handleUltrasonicAttach(JsonVariantConst payload, CommandContext& ctx);
    void handleUltrasonicRead(JsonVariantConst payload, CommandContext& ctx);
    void handleEncoderAttach(JsonVariantConst payload, CommandContext& ctx);
    void handleEncoderRead(JsonVariantConst payload, CommandContext& ctx);
    void handleEncoderReset(JsonVariantConst payload, CommandContext& ctx);
};
