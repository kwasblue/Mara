// include/command/handlers/IdentityHandler.h
// Handles device identity and capability queries

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "config/DeviceManifest.h"
#include "config/Version.h"
#include "core/Debug.h"

class IdentityHandler : public ICommandHandler {
public:
    IdentityHandler() = default;

    const char* name() const override { return "IdentityHandler"; }

    bool canHandle(CmdType cmd) const override {
        return cmd == CmdType::GET_IDENTITY;
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        if (cmd == CmdType::GET_IDENTITY) {
            handleGetIdentity(ctx);
        }
    }

private:
    void handleGetIdentity(CommandContext& ctx) {
        DBG_PRINTLN("[IDENTITY] GET_IDENTITY");

        // Build capability mask from compile-time flags
        uint32_t caps = mara::buildDeviceCaps();

        JsonDocument resp;

        // Version info
        resp["firmware"] = Version::FIRMWARE;
        resp["protocol"] = Version::PROTOCOL;
        resp["schema"] = Version::SCHEMA_VERSION;
        resp["board"] = Version::BOARD;
        resp["name"] = Version::NAME;

        // Capability bitmask (for programmatic use)
        resp["caps"] = caps;

        // Human-readable feature list
        JsonArray features = resp["features"].to<JsonArray>();

        // Add features based on capability bits
        if (caps & mara::DeviceCap::UART) features.add("uart");
        if (caps & mara::DeviceCap::WIFI) features.add("wifi");
        if (caps & mara::DeviceCap::DC_MOTOR) features.add("dc_motor");
        if (caps & mara::DeviceCap::SERVO) features.add("servo");
        if (caps & mara::DeviceCap::STEPPER) features.add("stepper");
        if (caps & mara::DeviceCap::ENCODER) features.add("encoder");
        if (caps & mara::DeviceCap::IMU) features.add("imu");
        if (caps & mara::DeviceCap::TELEMETRY) features.add("telemetry");
        if (caps & mara::DeviceCap::SIGNAL_BUS) features.add("signal_bus");
        if (caps & mara::DeviceCap::CONTROL_KERNEL) features.add("control_kernel");

        ctx.sendAck("CMD_GET_IDENTITY", true, resp);
    }
};
