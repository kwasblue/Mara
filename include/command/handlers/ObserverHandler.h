// include/command/handlers/ObserverHandler.h
// Handles observer commands for state estimation

#pragma once

#include "command/ICommandHandler.h"
#include "command/CommandContext.h"
#include "command/decoders/ObserverDecoders.h"
#include "command/decoders/ControlDecoders.h"  // For extractFloatArray
#include "module/ControlModule.h"
#include "core/Debug.h"

class ObserverHandler : public ICommandHandler {
public:
    ObserverHandler() : controlModule_(nullptr) {}

    void setControlModule(ControlModule* cm) { controlModule_ = cm; }

    const char* name() const override { return "ObserverHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::OBSERVER_CONFIG:
            case CmdType::OBSERVER_ENABLE:
            case CmdType::OBSERVER_RESET:
            case CmdType::OBSERVER_SET_PARAM:
            case CmdType::OBSERVER_SET_PARAM_ARRAY:
            case CmdType::OBSERVER_STATUS:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::OBSERVER_CONFIG:          handleConfig(payload, ctx);        break;
            case CmdType::OBSERVER_ENABLE:          handleEnable(payload, ctx);        break;
            case CmdType::OBSERVER_RESET:           handleReset(payload, ctx);         break;
            case CmdType::OBSERVER_SET_PARAM:       handleSetParam(payload, ctx);      break;
            case CmdType::OBSERVER_SET_PARAM_ARRAY: handleSetParamArray(payload, ctx); break;
            case CmdType::OBSERVER_STATUS:          handleStatus(payload, ctx);        break;
            default: break;
        }
    }

private:
    ControlModule* controlModule_;

    void handleConfig(JsonVariantConst payload, CommandContext& ctx) {
        static constexpr const char* ACK = "CMD_OBSERVER_CONFIG";

        if (!ctx.requireIdle(ACK)) return;
        if (!controlModule_) { ctx.sendError(ACK, "no_control_module"); return; }

        auto result = mara::cmd::decodeObserverConfig(payload);
        if (!result.valid) { ctx.sendError(ACK, result.error); return; }

        bool ok = controlModule_->observers().configure(result.slot, result.config, result.rate_hz);

        JsonDocument resp;
        resp["slot"] = result.slot;
        resp["num_states"] = result.config.num_states;
        resp["num_inputs"] = result.config.num_inputs;
        resp["num_outputs"] = result.config.num_outputs;
        resp["rate_hz"] = result.rate_hz;
        if (!ok) resp["error"] = "config_failed";
        ctx.sendAck(ACK, ok, resp);
    }

    void handleEnable(JsonVariantConst payload, CommandContext& ctx) {
        static constexpr const char* ACK = "CMD_OBSERVER_ENABLE";

        if (!controlModule_) {
            ctx.sendError(ACK, "no_control_module");
            return;
        }

        uint8_t slot = payload["slot"] | 0;
        bool enable = payload["enable"] | true;

        bool ok = controlModule_->observers().enable(slot, enable);

        JsonDocument resp;
        resp["slot"] = slot;
        resp["enable"] = enable;
        if (!ok) {
            resp["error"] = "enable_failed";
        }
        ctx.sendAck(ACK, ok, resp);
    }

    void handleReset(JsonVariantConst payload, CommandContext& ctx) {
        static constexpr const char* ACK = "CMD_OBSERVER_RESET";

        if (!controlModule_) {
            ctx.sendError(ACK, "no_control_module");
            return;
        }

        uint8_t slot = payload["slot"] | 0;
        bool ok = controlModule_->observers().reset(slot);

        JsonDocument resp;
        resp["slot"] = slot;
        if (!ok) {
            resp["error"] = "reset_failed";
        }
        ctx.sendAck(ACK, ok, resp);
    }

    void handleSetParam(JsonVariantConst payload, CommandContext& ctx) {
        static constexpr const char* ACK = "CMD_OBSERVER_SET_PARAM";

        if (!controlModule_) {
            ctx.sendError(ACK, "no_control_module");
            return;
        }

        uint8_t slot = payload["slot"] | 0;
        const char* key = payload["key"] | "";
        float value = payload["value"] | 0.0f;

        if (!key || strlen(key) < 3) {
            ctx.sendError(ACK, "invalid_key");
            return;
        }

        bool ok = controlModule_->observers().setParam(slot, key, value);

        JsonDocument resp;
        resp["slot"] = slot;
        resp["key"] = key;
        resp["value"] = value;
        if (!ok) {
            resp["error"] = "set_param_failed";
        }
        ctx.sendAck(ACK, ok, resp);
    }

    void handleSetParamArray(JsonVariantConst payload, CommandContext& ctx) {
        static constexpr const char* ACK = "CMD_OBSERVER_SET_PARAM_ARRAY";

        if (!controlModule_) { ctx.sendError(ACK, "no_control_module"); return; }

        uint8_t slot = payload["slot"] | 0;
        const char* key = payload["key"] | "";
        JsonArrayConst arr = payload["values"].as<JsonArrayConst>();

        if (!arr || arr.size() == 0) {
            JsonDocument resp;
            resp["slot"] = slot;
            resp["key"] = key;
            resp["error"] = "missing_values";
            ctx.sendAck(ACK, false, resp);
            return;
        }

        // Extract float array (max 36 for 6x6 matrix)
        float values[36];
        size_t len = mara::cmd::extractFloatArray(arr, values, sizeof(values) / sizeof(values[0]));

        bool ok = controlModule_->observers().setParamArray(slot, key, values, len);

        JsonDocument resp;
        resp["slot"] = slot;
        resp["key"] = key;
        resp["count"] = static_cast<int>(len);
        if (!ok) resp["error"] = "set_param_array_failed";
        ctx.sendAck(ACK, ok, resp);
    }

    void handleStatus(JsonVariantConst payload, CommandContext& ctx) {
        static constexpr const char* ACK = "CMD_OBSERVER_STATUS";

        if (!controlModule_) {
            ctx.sendError(ACK, "no_control_module");
            return;
        }

        uint8_t slot = payload["slot"] | 0;
        const auto& s = controlModule_->observers().getSlot(slot);

        JsonDocument resp;
        resp["slot"] = slot;
        resp["configured"] = s.configured;
        resp["enabled"] = s.enabled;
        resp["rate_hz"] = s.rate_hz;
        resp["initialized"] = s.observer.isInitialized();
        resp["update_count"] = s.update_count;

        // Current state estimates
        JsonArray estimates = resp["estimates"].to<JsonArray>();
        for (uint8_t i = 0; i < s.config.num_states; i++) {
            estimates.add(s.observer.getState(i));
        }

        ctx.sendAck(ACK, true, resp);
    }
};
