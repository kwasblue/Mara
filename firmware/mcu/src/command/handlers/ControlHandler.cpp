// src/command/handlers/ControlHandler.cpp
// Implementation of ControlHandler methods

#include "command/handlers/ControlHandler.h"
#include "module/ControlModule.h"
#include "core/ServiceContext.h"
#include "command/decoders/ControlDecoders.h"
#include "core/Debug.h"
#include "persistence/McuPersistence.h"

void ControlHandler::init(mara::ServiceContext& ctx) {
    controlModule_ = ctx.control;
}

// -------------------------------------------------------------------------
// Signal Commands
// -------------------------------------------------------------------------

void ControlHandler::handleSignalDefine(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SIGNAL_DEFINE";

    // Signal defines require ARMED or ACTIVE - IDLE is read-only
    if (!ctx.requireArmedOrActive(ACK)) return;
    if (!controlModule_) { ctx.sendError(ACK, "no_control_module"); return; }

    auto result = mara::cmd::decodeSignalDef(payload);
    if (!result.valid) { ctx.sendError(ACK, result.error); return; }

    const char* kindS = signalKindToString(result.kind);
    DBG_PRINTF("[CTRL] SIGNAL_DEFINE: id=%u name=%s kind=%s initial=%.2f\n",
               result.id, result.name, kindS, result.initial);

    bool ok = controlModule_->signals().define(result.id, result.name, result.kind, result.initial);

    JsonDocument resp;
    resp["id"] = result.id;
    resp["name"] = result.name;
    resp["kind"] = kindS;
    resp["initial"] = result.initial;
    if (!ok) resp["error"] = "define_failed";
    ctx.sendAck(ACK, ok, resp);
}

void ControlHandler::handleSignalSet(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SIGNAL_SET";

    if (!controlModule_) {
        ctx.sendError(ACK, "no_control_module");
        return;
    }

    uint16_t id = payload["id"] | 0;
    float value = payload["value"] | 0.0f;
    const uint32_t now_ms = ctx.now_ms();

    bool ok = true;
    // Queue signal intent (control task will consume and apply)
    if (ctx.intents) {
        ctx.intents->queueSignalIntent(id, value, now_ms);
    } else {
        // Fallback: Direct write bypasses intent buffer's FIFO ordering.
        // This path indicates misconfigured context - signal writes will be
        // out-of-phase with the control loop (applied immediately from handler
        // task rather than at control tick time).
        DBG_PRINTF("[CTRL] WARNING: Signal %u set via fallback (no intent buffer)\n", id);
        ok = controlModule_->signals().set(id, value, now_ms);
    }

    JsonDocument resp;
    resp["id"] = id;
    resp["value"] = value;
    if (!ok) {
        resp["error"] = "signal_not_found";
    }
    ctx.sendAck(ACK, ok, resp);
}

void ControlHandler::handleSignalGet(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SIGNAL_GET";

    if (!controlModule_) {
        ctx.sendError(ACK, "no_control_module");
        return;
    }

    uint16_t id = payload["id"] | 0;
    float value = 0.0f;
    bool ok = controlModule_->signals().get(id, value);

    JsonDocument resp;
    resp["id"] = id;
    resp["value"] = value;
    if (!ok) {
        resp["error"] = "signal_not_found";
    }
    ctx.sendAck(ACK, ok, resp);
}

void ControlHandler::handleSignalsList(CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SIGNALS_LIST";

    JsonDocument resp;

    if (!controlModule_) {
        resp["count"] = 0;
        resp["signals"].to<JsonArray>();
        ctx.sendAck(ACK, true, resp);
        return;
    }

    const auto& vec = controlModule_->signals().all();
    resp["count"] = static_cast<uint16_t>(vec.size());
    JsonArray arr = resp["signals"].to<JsonArray>();

    for (const auto& sdef : vec) {
        JsonObject s = arr.add<JsonObject>();
        s["id"] = sdef.id;
        s["name"] = sdef.name;
        s["kind"] = signalKindToString(sdef.kind);
        s["value"] = sdef.value;
        s["ts_ms"] = sdef.ts_ms;
    }

    ctx.sendAck(ACK, true, resp);
}

void ControlHandler::handleSignalDelete(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SIGNAL_DELETE";

    if (!controlModule_) {
        ctx.sendError(ACK, "no_control_module");
        return;
    }

    uint16_t id = payload["id"] | 0;
    bool ok = controlModule_->signals().remove(id);

    JsonDocument resp;
    resp["id"] = id;
    resp["deleted"] = ok;
    ctx.sendAck(ACK, ok, resp);
}

void ControlHandler::handleSignalsClear(CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SIGNALS_CLEAR";

    if (!controlModule_) {
        ctx.sendError(ACK, "no_control_module");
        return;
    }

    controlModule_->signals().clear();

    JsonDocument resp;
    resp["cleared"] = true;
    resp["count"] = 0;
    ctx.sendAck(ACK, true, resp);
}

void ControlHandler::handleSignalTrace(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SIGNAL_TRACE";

    if (!controlModule_) {
        ctx.sendError(ACK, "no_control_module");
        return;
    }

    // Parse signal IDs array
    JsonArrayConst ids = payload["signal_ids"].as<JsonArrayConst>();
    uint16_t rate_hz = payload["rate_hz"] | 10;

    // Validate rate (1-50Hz)
    if (rate_hz < 1) rate_hz = 1;
    if (rate_hz > 50) rate_hz = 50;

    SignalBus& bus = controlModule_->signals();

    if (!ids || ids.size() == 0) {
        // Disable tracing
        bus.setTraceSignals(nullptr, 0, 0);
        JsonDocument resp;
        resp["tracing"] = false;
        resp["count"] = 0;
        ctx.sendAck(ACK, true, resp);
        return;
    }

    // Convert to array of IDs
    uint16_t signalIds[16];
    size_t count = 0;
    for (JsonVariantConst idVar : ids) {
        if (count >= 16) break;
        signalIds[count++] = static_cast<uint16_t>(idVar.as<int>());
    }

    bus.setTraceSignals(signalIds, count, rate_hz);

    JsonDocument resp;
    resp["tracing"] = true;
    resp["count"] = bus.isTraceEnabled() ? static_cast<int>(count) : 0;
    resp["rate_hz"] = rate_hz;
    ctx.sendAck(ACK, true, resp);
}

void ControlHandler::handleAutoSignalsConfig(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_AUTO_SIGNALS_CONFIG";

    // Auto-signals config requires ARMED or ACTIVE - IDLE is read-only
    if (!ctx.requireArmedOrActive(ACK)) return;

    // This handler requires access to sensor managers via ServiceContext
    // For now, send error - full implementation requires ServiceContext wiring
    ctx.sendError(ACK, "not_implemented");
}

// -------------------------------------------------------------------------
// Slot Commands
// -------------------------------------------------------------------------

void ControlHandler::handleSlotConfig(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SLOT_CONFIG";

    // Slot config requires ARMED or ACTIVE - IDLE is read-only
    if (!ctx.requireArmedOrActive(ACK)) return;
    if (!controlModule_) { ctx.sendError(ACK, "no_control_module"); return; }

    auto result = mara::cmd::decodeSlotConfig(payload);
    if (!result.valid) { ctx.sendError(ACK, result.error); return; }

    bool ok = controlModule_->kernel().configureSlot(result.config, result.controllerType);

    JsonDocument resp;
    resp["slot"] = result.config.slot;
    resp["controller_type"] = result.controllerType;
    resp["rate_hz"] = result.config.rate_hz;
    if (!ok) resp["error"] = "config_failed";
    ctx.sendAck(ACK, ok, resp);
}

void ControlHandler::handleSlotEnable(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SLOT_ENABLE";

    if (!controlModule_) {
        ctx.sendError(ACK, "no_control_module");
        return;
    }

    uint8_t slot = payload["slot"] | 0;
    bool enable = payload["enable"] | true;

    bool ok = controlModule_->kernel().enableSlot(slot, enable);

    JsonDocument resp;
    resp["slot"] = slot;
    resp["enable"] = enable;
    if (!ok) {
        resp["error"] = "enable_failed";
    }
    ctx.sendAck(ACK, ok, resp);
}

void ControlHandler::handleSlotReset(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SLOT_RESET";

    if (!controlModule_) {
        ctx.sendError(ACK, "no_control_module");
        return;
    }

    uint8_t slot = payload["slot"] | 0;
    bool ok = controlModule_->kernel().resetSlot(slot);

    JsonDocument resp;
    resp["slot"] = slot;
    if (!ok) {
        resp["error"] = "reset_failed";
    }
    ctx.sendAck(ACK, ok, resp);
}

void ControlHandler::handleSlotSetParam(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SLOT_SET_PARAM";

    if (!controlModule_) {
        ctx.sendError(ACK, "no_control_module");
        return;
    }

    uint8_t slot = payload["slot"] | 0;
    const char* key = payload["key"] | "";
    float value = payload["value"] | 0.0f;

    if (!key || key[0] == '\0') {
        ctx.sendError(ACK, "missing_key");
        return;
    }

    bool ok = controlModule_->kernel().setParam(slot, key, value);

    JsonDocument resp;
    resp["slot"] = slot;
    resp["key"] = key;
    resp["value"] = value;
    if (!ok) {
        resp["error"] = "set_param_failed";
    }
    ctx.sendAck(ACK, ok, resp);
}

void ControlHandler::handleSlotSetParamArray(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SLOT_SET_PARAM_ARRAY";

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

    // Buffer sized from actual constants to prevent silent truncation if they change
    static constexpr size_t MAX_ARRAY_SIZE = StateSpaceIO::MAX_INPUTS * StateSpaceIO::MAX_STATES;
    float values[MAX_ARRAY_SIZE];
    size_t len = mara::cmd::extractFloatArray(arr, values, MAX_ARRAY_SIZE);

    bool ok = controlModule_->kernel().setParamArray(slot, key, values, len);

    JsonDocument resp;
    resp["slot"] = slot;
    resp["key"] = key;
    resp["count"] = static_cast<int>(len);
    if (!ok) resp["error"] = "set_param_array_failed";
    ctx.sendAck(ACK, ok, resp);
}

void ControlHandler::handleSlotGetParam(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SLOT_GET_PARAM";

    if (!controlModule_) {
        ctx.sendError(ACK, "no_control_module");
        return;
    }

    uint8_t slot = payload["slot"] | 0;
    const char* key = payload["key"] | "";

    if (!key || key[0] == '\0') {
        ctx.sendError(ACK, "missing_key");
        return;
    }

    float value = 0.0f;
    bool ok = controlModule_->kernel().getParam(slot, key, value);

    JsonDocument resp;
    resp["slot"] = slot;
    resp["key"] = key;
    resp["value"] = value;
    if (!ok) {
        resp["error"] = "get_param_failed";
    }
    ctx.sendAck(ACK, ok, resp);
}

void ControlHandler::handleSlotStatus(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_SLOT_STATUS";

    if (!controlModule_) {
        ctx.sendError(ACK, "no_control_module");
        return;
    }

    uint8_t slot = payload["slot"] | 0;

    auto cfg = controlModule_->kernel().getConfig(slot);
    auto st = controlModule_->kernel().getStatus(slot);

    JsonDocument resp;
    resp["slot"] = slot;
    resp["enabled"] = cfg.enabled;
    resp["rate_hz"] = cfg.rate_hz;
    resp["ok"] = st.ok;
    resp["run_count"] = st.run_count;
    resp["last_run_ms"] = st.last_run_ms;
    if (st.last_error) {
        resp["last_error"] = st.last_error;
    }
    ctx.sendAck(ACK, true, resp);
}

void ControlHandler::handleGraphUpload(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_GRAPH_UPLOAD";

    // Graph upload requires ARMED or ACTIVE - IDLE is read-only
    if (!ctx.requireArmedOrActive(ACK)) return;
    if (!controlModule_) { ctx.sendError(ACK, "no_control_module"); return; }

    JsonVariantConst graph = payload["graph"];
    const bool commit = payload["commit"] | true;  // Default to immediate commit
    const char* modeStr = payload["mode"] | "replace";
    const char* error = nullptr;

    // Parse upload mode
    ControlGraphRuntime::UploadMode mode = ControlGraphRuntime::UploadMode::Replace;
    if (strcmp(modeStr, "merge") == 0) {
        mode = ControlGraphRuntime::UploadMode::Merge;
    }

    JsonDocument resp;

    if (commit) {
        // Immediate activation
        bool ok = controlModule_->graph().upload(graph, error, mode);
        resp["present"] = ok;
        resp["schema_version"] = ok ? controlModule_->graph().schemaVersion() : 0;
        resp["slot_count"] = ok ? controlModule_->graph().slotCount() : 0;
        resp["committed"] = ok;
        resp["mode"] = modeStr;
        if (!ok && error) {
            resp["error"] = error;
        }
        ctx.sendAck(ACK, ok, resp);
    } else {
        // Two-phase commit: stage pending (mode applies on commit)
        bool ok = controlModule_->graph().uploadPending(graph, error, ctx.now_ms());
        resp["pending"] = ok;
        if (ok) {
            const auto& pending = controlModule_->graph().pendingInfo();
            resp["token"] = pending.token;
            resp["hash"] = pending.hash;
            resp["slot_count"] = pending.slot_count;
            resp["committed"] = false;
        }
        if (!ok && error) {
            resp["error"] = error;
        }
        ctx.sendAck(ACK, ok, resp);
    }
}

void ControlHandler::handleGraphCommit(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_GRAPH_COMMIT";

    // Graph commit requires ARMED or ACTIVE - IDLE is read-only
    if (!ctx.requireArmedOrActive(ACK)) return;
    if (!controlModule_) { ctx.sendError(ACK, "no_control_module"); return; }

    uint32_t token = payload["token"] | 0;
    const char* error = nullptr;

    bool ok = controlModule_->graph().commitPending(token, error, ctx.now_ms());

    JsonDocument resp;
    resp["committed"] = ok;
    if (ok) {
        resp["present"] = controlModule_->graph().present();
        resp["schema_version"] = controlModule_->graph().schemaVersion();
        resp["slot_count"] = controlModule_->graph().slotCount();
    }
    if (!ok && error) {
        resp["error"] = error;
    }
    ctx.sendAck(ACK, ok, resp);
}

void ControlHandler::handleGraphClear(CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_GRAPH_CLEAR";

    if (!controlModule_) { ctx.sendError(ACK, "no_control_module"); return; }
    controlModule_->graph().clear();

    JsonDocument resp;
    resp["cleared"] = true;
    resp["present"] = false;
    resp["slot_count"] = 0;
    ctx.sendAck(ACK, true, resp);
}

void ControlHandler::handleGraphEnable(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_GRAPH_ENABLE";

    if (!controlModule_) { ctx.sendError(ACK, "no_control_module"); return; }
    if (!controlModule_->graph().present()) { ctx.sendError(ACK, "graph_not_present"); return; }

    bool enable = payload["enable"] | true;
    controlModule_->graph().setEnabled(enable);

    JsonDocument resp;
    resp["present"] = true;
    resp["enabled"] = controlModule_->graph().enabled();
    resp["slot_count"] = controlModule_->graph().slotCount();
    ctx.sendAck(ACK, true, resp);
}

void ControlHandler::handleGraphStatus(CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_GRAPH_STATUS";

    if (!controlModule_) { ctx.sendError(ACK, "no_control_module"); return; }

    const auto& graph = controlModule_->graph();
    const uint32_t now_ms = ctx.now_ms();
    JsonDocument resp;
    resp["present"] = graph.present();
    resp["enabled"] = graph.enabled();
    resp["schema_version"] = graph.schemaVersion();
    resp["slot_count"] = graph.slotCount();
    JsonArray slots = resp["slots"].to<JsonArray>();
    for (uint8_t i = 0; i < graph.slotCount(); ++i) {
        const auto& slot = graph.slot(i);
        const auto& runtime = graph.runtimeSlot(i);
        JsonObject out = slots.add<JsonObject>();
        out["id"] = slot.id;
        out["enabled"] = slot.enabled;
        out["rate_hz"] = slot.rate_hz;
        out["source_type"] = slot.source_type;
        out["sink_type"] = slot.sink_type;
        out["transform_count"] = slot.transform_count;
        out["valid"] = runtime.valid;
        out["run_count"] = runtime.run_count;
        out["last_run_ms"] = runtime.last_run_ms;
        out["sink_count"] = runtime.sink_count;
        // For backwards compatibility, report first sink's output state
        out["last_output_high"] = (runtime.sink_count > 0) ? runtime.sinks[0].last_output_high : false;
        if (runtime.error[0]) {
            out["error"] = runtime.error;
        }

        // Health monitoring info
        out["healthy"] = graph.isSlotHealthy(i, now_ms);
        out["actual_hz"] = graph.getSlotActualHz(i);
        out["actual_period_us"] = runtime.actual_period_us;
        out["min_period_us"] = runtime.min_period_us;
        out["max_period_us"] = runtime.max_period_us;
    }
    ctx.sendAck(ACK, true, resp);
}

void ControlHandler::handleGraphDebug(JsonVariantConst payload, CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_CTRL_GRAPH_DEBUG";

    if (!controlModule_) { ctx.sendError(ACK, "no_control_module"); return; }
    if (!controlModule_->graph().present()) { ctx.sendError(ACK, "graph_not_present"); return; }

    const char* slotId = payload["slot_id"] | "";

    // Empty string or null disables debug mode
    bool ok = controlModule_->graph().setDebugSlot(slotId);

    JsonDocument resp;
    if (!ok) {
        resp["error"] = "slot_not_found";
        resp["slot_id"] = slotId;
        ctx.sendAck(ACK, false, resp);
        return;
    }

    // Return current debug state
    resp["debug_enabled"] = (controlModule_->graph().debugSlotIdx() >= 0);
    const char* currentSlotId = controlModule_->graph().debugSlotId();
    if (currentSlotId) {
        resp["slot_id"] = currentSlotId;
    } else {
        resp["slot_id"] = nullptr;
    }
    ctx.sendAck(ACK, true, resp);
}

void ControlHandler::handleMcuDiagnosticsQuery(CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_MCU_DIAGNOSTICS_QUERY";

    if (!ctx.persistence) {
        ctx.sendError(ACK, "persistence_unavailable");
        return;
    }

    JsonDocument resp;
    ctx.persistence->fillSnapshot(resp.to<JsonObject>());
    ctx.sendAck(ACK, true, resp);
}

void ControlHandler::handleMcuDiagnosticsReset(CommandContext& ctx) {
    static constexpr const char* ACK = "CMD_MCU_DIAGNOSTICS_RESET";

    if (!ctx.persistence) {
        ctx.sendError(ACK, "persistence_unavailable");
        return;
    }

    ctx.persistence->resetDiagnostics(ctx.now_ms());

    JsonDocument resp;
    resp["reset"] = true;
    JsonObject snapshot = resp["snapshot"].to<JsonObject>();
    ctx.persistence->fillSnapshot(snapshot);
    resp["ready"] = ctx.persistence->ready();
    JsonObject diagnostics = resp["diagnostics"].to<JsonObject>();
    ctx.persistence->fillDiagnostics(diagnostics);
    ctx.sendAck(ACK, true, resp);
}
