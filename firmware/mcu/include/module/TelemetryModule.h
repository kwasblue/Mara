// modules/TelemetryModule.h
#pragma once

#include "core/IModule.h"
#include "core/EventBus.h"
#include "core/Event.h"

#include <ArduinoJson.h>
#include <array>
#include <cstddef>
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

    struct PacketStats {
        uint32_t sent_packets = 0;
        uint32_t sent_bytes = 0;
        uint32_t dropped_sections = 0;
        uint16_t last_packet_bytes = 0;
        uint16_t max_packet_bytes = 0;
        uint8_t last_section_count = 0;
        uint8_t max_section_count = 0;
        uint32_t last_emit_ms = 0;
        uint32_t last_drop_ms = 0;
        uint16_t buffered_packets = 0;
    };

    struct PacketRecord {
        uint32_t ts_ms = 0;
        uint16_t bytes = 0;
        uint8_t sections = 0;
        uint8_t dropped_sections = 0;
    };

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

    const PacketStats& packetStats() const { return packetStats_; }
    const PacketRecord* packetHistory(size_t& count, size_t& head) const;

private:
    struct JsonProvider {
        std::string name;
        JsonProviderFn fn;
    };

    struct BinProvider {
        uint8_t section_id;
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

    static constexpr size_t PACKET_HISTORY_SIZE = 32;
    std::array<PacketRecord, PACKET_HISTORY_SIZE> packetHistory_{};
    size_t packetHistoryHead_ = 0;
    size_t packetHistoryCount_ = 0;
    PacketStats packetStats_{};

    // Pre-allocated JSON document to avoid heap allocation per emit
    ArduinoJson::JsonDocument jsonDoc_;

    void recordPacket(uint32_t now_ms, size_t bytes, uint8_t sectionCount, uint8_t droppedSections);
    void sendTelemetry(uint32_t now_ms);

    // Packing helpers (LE)
    static void put_u8 (std::vector<uint8_t>& b, uint8_t  v);
    static void put_u16(std::vector<uint8_t>& b, uint16_t v);
    static void put_u32(std::vector<uint8_t>& b, uint32_t v);
};
