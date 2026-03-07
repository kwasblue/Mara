// modules/TelemetryModule.h
#pragma once

#include "core/IModule.h"
#include "core/EventBus.h"
#include "core/Event.h"

#include <ArduinoJson.h>
#include <cstdint>
#include <functional>
#include <string>
#include <vector>

// TelemetryModule:
// - Periodic telemetry publisher
// - Can emit telemetry as either:
//    (A) JSON aggregate packet (debug/legacy) -> EventType::JSON_MESSAGE_TX
//    (B) Binary "sectioned" packet (recommended) -> EventType::BIN_MESSAGE_TX
class TelemetryModule : public IModule {
public:
    using JsonProviderFn = std::function<void(ArduinoJson::JsonObject&)>;
    using BinProviderFn  = std::function<void(std::vector<uint8_t>& out)>;

    explicit TelemetryModule(EventBus& bus);
    const char* name() const override { return "TelemetryModule"; }

    void setup() override;
    void loop(uint32_t now_ms) override;

    // Providers
    void registerProvider(const char* name, JsonProviderFn fn);
    void registerBinProvider(uint8_t section_id, BinProviderFn fn);

    // Timing
    void setInterval(uint32_t intervalMs); // default 100ms (10Hz)

    // Output toggles
    void setBinaryEnabled(bool en);
    void setJsonEnabled(bool en);

private:
    struct JsonProvider {
        std::string   name;
        JsonProviderFn fn;
    };

    struct BinProvider {
        uint8_t       section_id;
        BinProviderFn fn;
    };

    EventBus& bus_;

    std::vector<JsonProvider> jsonProviders_;
    std::vector<BinProvider>  binProviders_;

    uint32_t lastTickMs_ = 0;
    uint32_t intervalMs_ = 100;

    bool binaryEnabled_ = true;
    bool jsonEnabled_   = false;

    uint16_t seq_ = 0;

    std::vector<uint8_t> txBuf_;
    std::vector<uint8_t> sectionBuf_;

    // Pre-allocated JSON document to avoid heap allocation per emit
    ArduinoJson::JsonDocument jsonDoc_;

    void sendTelemetry(uint32_t now_ms);

    // Packing helpers (LE)
    static void put_u8 (std::vector<uint8_t>& b, uint8_t  v);
    static void put_u16(std::vector<uint8_t>& b, uint16_t v);
    static void put_u32(std::vector<uint8_t>& b, uint32_t v);
};
