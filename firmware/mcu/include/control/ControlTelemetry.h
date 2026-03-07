// src/telemetry/ControlTelemetryProvider.h
// Provides telemetry for the control system: signals, observers, and slots
#pragma once

#include <ArduinoJson.h>
#include "control/SignalBus.h"
#include "control/ControlKernel.h"
#include "control/Observer.h"

namespace ControlTelemetry {

// Binary telemetry section IDs (add to your existing section IDs)
constexpr uint8_t SECTION_SIGNALS   = 0x10;  // Signal bus values
constexpr uint8_t SECTION_OBSERVERS = 0x11;  // Observer state estimates
constexpr uint8_t SECTION_SLOTS     = 0x12;  // Control slot status

// ============================================================================
// JSON Telemetry Providers
// ============================================================================

/**
 * Provides JSON telemetry for signal bus
 * Output: { "signals": [ {id, name, value, ts_ms}, ... ], "count": N }
 */
inline void provideSignalsJson(JsonObject& out, const SignalBus& bus) {
    const auto& signals = bus.all();
    out["count"] = static_cast<uint16_t>(signals.size());

    JsonArray arr = out["signals"].to<JsonArray>();
    for (const auto& s : signals) {
        JsonObject sig = arr.add<JsonObject>();
        sig["id"] = s.id;
        sig["n"] = s.name;  // Short key for bandwidth
        sig["v"] = s.value;
        sig["t"] = s.ts_ms;
    }
}

/**
 * Provides JSON telemetry for observer estimates
 * Output: { "observers": [ {slot, enabled, states: [x0, x1, ...]}, ... ] }
 */
inline void provideObserversJson(JsonObject& out, const ObserverManager& mgr) {
    JsonArray arr = out["observers"].to<JsonArray>();
    
    for (uint8_t slot = 0; slot < ObserverManager::MAX_SLOTS; ++slot) {
        const auto& s = mgr.getSlot(slot);
        if (!s.configured) continue;
        
        JsonObject obs = arr.add<JsonObject>();
        obs["slot"] = slot;
        obs["en"] = s.enabled;
        obs["cnt"] = s.update_count;
        
        // State estimates
        JsonArray states = obs["x"].to<JsonArray>();
        for (uint8_t i = 0; i < s.config.num_states; ++i) {
            states.add(s.observer.getState(i));
        }
    }
}

/**
 * Provides JSON telemetry for control slots
 * Output: { "slots": [ {slot, enabled, ok, run_count, last_run_ms}, ... ] }
 */
inline void provideSlotsJson(JsonObject& out, const ControlKernel& kernel) {
    JsonArray arr = out["slots"].to<JsonArray>();
    
    for (uint8_t slot = 0; slot < ControlKernel::MAX_SLOTS; ++slot) {
        auto cfg = kernel.getConfig(slot);
        if (!cfg.enabled && cfg.rate_hz == 0) continue;  // Skip unconfigured
        
        auto st = kernel.getStatus(slot);
        
        JsonObject s = arr.add<JsonObject>();
        s["slot"] = slot;
        s["en"] = cfg.enabled;
        s["ok"] = st.ok;
        s["cnt"] = st.run_count;
        s["last"] = st.last_run_ms;
        if (st.last_error) {
            s["err"] = st.last_error;
        }
    }
}

/**
 * Combined control telemetry (signals + observers + slots)
 */
inline void provideControlJson(JsonObject& out, const SignalBus& bus,
                               const ControlKernel& kernel, const ObserverManager& observers) {
    JsonObject sig = out["sig"].to<JsonObject>();
    provideSignalsJson(sig, bus);
    
    JsonObject obs = out["obs"].to<JsonObject>();
    provideObserversJson(obs, observers);
    
    JsonObject slt = out["slt"].to<JsonObject>();
    provideSlotsJson(slt, kernel);
}

// ============================================================================
// Binary Telemetry Providers (more efficient for high-rate streaming)
// ============================================================================

/**
 * Binary format for signals:
 * [count:u16] [id:u16, value:f32, ts_ms:u32] * count
 */
inline size_t provideSignalsBin(uint8_t* buf, size_t max_len, const SignalBus& bus) {
    const auto& signals = bus.all();
    size_t count = signals.size();
    
    // Header: count (2 bytes)
    size_t needed = 2 + count * (2 + 4 + 4);  // id + value + ts
    if (needed > max_len) return 0;
    
    size_t pos = 0;
    
    // Count (little-endian)
    buf[pos++] = count & 0xFF;
    buf[pos++] = (count >> 8) & 0xFF;
    
    // Each signal: id(u16) + value(f32) + ts_ms(u32)
    for (const auto& s : signals) {
        // ID
        buf[pos++] = s.id & 0xFF;
        buf[pos++] = (s.id >> 8) & 0xFF;
        
        // Value (IEEE 754 float, little-endian)
        uint32_t v;
        memcpy(&v, &s.value, 4);
        buf[pos++] = v & 0xFF;
        buf[pos++] = (v >> 8) & 0xFF;
        buf[pos++] = (v >> 16) & 0xFF;
        buf[pos++] = (v >> 24) & 0xFF;
        
        // Timestamp
        buf[pos++] = s.ts_ms & 0xFF;
        buf[pos++] = (s.ts_ms >> 8) & 0xFF;
        buf[pos++] = (s.ts_ms >> 16) & 0xFF;
        buf[pos++] = (s.ts_ms >> 24) & 0xFF;
    }
    
    return pos;
}

/**
 * Binary format for observer states:
 * [slot_count:u8] [slot:u8, enabled:u8, num_states:u8, x[0]:f32, x[1]:f32, ...] * slot_count
 */
inline size_t provideObserversBin(uint8_t* buf, size_t max_len, const ObserverManager& mgr) {
    size_t pos = 0;
    
    // Count configured observers first
    uint8_t count = 0;
    for (uint8_t slot = 0; slot < ObserverManager::MAX_SLOTS; ++slot) {
        if (mgr.getSlot(slot).configured) count++;
    }
    
    if (max_len < 1) return 0;
    buf[pos++] = count;
    
    for (uint8_t slot = 0; slot < ObserverManager::MAX_SLOTS; ++slot) {
        const auto& s = mgr.getSlot(slot);
        if (!s.configured) continue;
        
        uint8_t n = s.config.num_states;
        size_t needed = 3 + n * 4;  // slot + enabled + num_states + n floats
        if (pos + needed > max_len) break;
        
        buf[pos++] = slot;
        buf[pos++] = s.enabled ? 1 : 0;
        buf[pos++] = n;
        
        // State estimates
        for (uint8_t i = 0; i < n; ++i) {
            float x = s.observer.getState(i);
            uint32_t v;
            memcpy(&v, &x, 4);
            buf[pos++] = v & 0xFF;
            buf[pos++] = (v >> 8) & 0xFF;
            buf[pos++] = (v >> 16) & 0xFF;
            buf[pos++] = (v >> 24) & 0xFF;
        }
    }
    
    return pos;
}

/**
 * Binary format for slot status:
 * [slot_count:u8] [slot:u8, enabled:u8, ok:u8, run_count:u32] * slot_count
 */
inline size_t provideSlotsBin(uint8_t* buf, size_t max_len, const ControlKernel& kernel) {
    size_t pos = 0;
    
    // Count configured slots
    uint8_t count = 0;
    for (uint8_t slot = 0; slot < ControlKernel::MAX_SLOTS; ++slot) {
        auto cfg = kernel.getConfig(slot);
        if (cfg.enabled || cfg.rate_hz > 0) count++;
    }
    
    if (max_len < 1) return 0;
    buf[pos++] = count;
    
    for (uint8_t slot = 0; slot < ControlKernel::MAX_SLOTS; ++slot) {
        auto cfg = kernel.getConfig(slot);
        if (!cfg.enabled && cfg.rate_hz == 0) continue;
        
        size_t needed = 7;  // slot + enabled + ok + run_count(4)
        if (pos + needed > max_len) break;
        
        auto st = kernel.getStatus(slot);
        
        buf[pos++] = slot;
        buf[pos++] = cfg.enabled ? 1 : 0;
        buf[pos++] = st.ok ? 1 : 0;
        
        buf[pos++] = st.run_count & 0xFF;
        buf[pos++] = (st.run_count >> 8) & 0xFF;
        buf[pos++] = (st.run_count >> 16) & 0xFF;
        buf[pos++] = (st.run_count >> 24) & 0xFF;
    }
    
    return pos;
}

} // namespace ControlTelemetry