// modules/TelemetryModule.cpp
#include "module/TelemetryModule.h"
#include "core/Debug.h"

#include <ArduinoJson.h>

static constexpr uint8_t TELEMETRY_BIN_VERSION = 1;

TelemetryModule::TelemetryModule(EventBus& bus)
    : bus_(bus) {
    txBuf_.reserve(256);
    sectionBuf_.reserve(128);
}

const TelemetryModule::PacketRecord* TelemetryModule::packetHistory(size_t& count, size_t& head) const {
    count = packetHistoryCount_;
    head = packetHistoryHead_;
    return packetHistory_.data();
}

void TelemetryModule::recordPacket(uint32_t now_ms, size_t bytes, uint8_t sectionCount, uint8_t droppedSections) {
    PacketRecord& slot = packetHistory_[packetHistoryHead_];
    slot.ts_ms = now_ms;
    slot.bytes = static_cast<uint16_t>(bytes > 0xFFFF ? 0xFFFF : bytes);
    slot.sections = sectionCount;
    slot.dropped_sections = droppedSections;

    packetHistoryHead_ = (packetHistoryHead_ + 1) % PACKET_HISTORY_SIZE;
    if (packetHistoryCount_ < PACKET_HISTORY_SIZE) ++packetHistoryCount_;

    packetStats_.sent_packets++;
    packetStats_.sent_bytes += static_cast<uint32_t>(bytes);
    packetStats_.last_packet_bytes = slot.bytes;
    if (slot.bytes > packetStats_.max_packet_bytes) packetStats_.max_packet_bytes = slot.bytes;
    packetStats_.last_section_count = sectionCount;
    if (sectionCount > packetStats_.max_section_count) packetStats_.max_section_count = sectionCount;
    packetStats_.dropped_sections += droppedSections;
    if (droppedSections > 0) packetStats_.last_drop_ms = now_ms;
    packetStats_.last_emit_ms = now_ms;
    packetStats_.buffered_packets = static_cast<uint16_t>(packetHistoryCount_);
}

void TelemetryModule::setup() {
    DBG_PRINTLN("[TelemetryModule] setup complete");
}

void TelemetryModule::loop(uint32_t now_ms) {
    if (intervalMs_ == 0) return;
    if ((now_ms - lastTickMs_) < intervalMs_) return;
    lastTickMs_ = now_ms;
    sendTelemetry(now_ms);
}

void TelemetryModule::setInterval(uint32_t intervalMs) {
    intervalMs_ = intervalMs;
    lastTickMs_ = 0;
}

void TelemetryModule::registerProvider(const char* name, JsonProviderFn fn) {
    if (!name || !fn) return;
    JsonProvider p{name, std::move(fn)};
    jsonProviders_.push_back(std::move(p));
    DBG_PRINTF("[TelemetryModule] registered JSON provider '%s'\n", name);
}

void TelemetryModule::registerBinProvider(uint8_t section_id, BinProviderFn fn) {
    if (!fn) return;
    if (section_id == 0) {
        DBG_PRINTLN("[TelemetryModule] refusing BIN provider with section_id=0");
        return;
    }
    for (auto& p : binProviders_) {
        if (p.section_id == section_id) {
            p.fn = std::move(fn);
            DBG_PRINTF("[TelemetryModule] updated BIN provider id=%u\n", (unsigned)section_id);
            return;
        }
    }
    binProviders_.push_back(BinProvider{section_id, std::move(fn)});
    DBG_PRINTF("[TelemetryModule] registered BIN provider id=%u\n", (unsigned)section_id);
}

void TelemetryModule::setBinaryEnabled(bool en) { binaryEnabled_ = en; }
void TelemetryModule::setJsonEnabled(bool en) { jsonEnabled_ = en; }

void TelemetryModule::put_u8(std::vector<uint8_t>& b, uint8_t v) { b.push_back(v); }
void TelemetryModule::put_u16(std::vector<uint8_t>& b, uint16_t v) {
    b.push_back(static_cast<uint8_t>(v & 0xFF));
    b.push_back(static_cast<uint8_t>((v >> 8) & 0xFF));
}
void TelemetryModule::put_u32(std::vector<uint8_t>& b, uint32_t v) {
    b.push_back(static_cast<uint8_t>(v & 0xFF));
    b.push_back(static_cast<uint8_t>((v >> 8) & 0xFF));
    b.push_back(static_cast<uint8_t>((v >> 16) & 0xFF));
    b.push_back(static_cast<uint8_t>((v >> 24) & 0xFF));
}

void TelemetryModule::sendTelemetry(uint32_t now_ms) {
    if (binaryEnabled_ && !binProviders_.empty()) {
        txBuf_.clear();
        const size_t n_all = binProviders_.size();
        const uint8_t count = (n_all > 255) ? 255 : static_cast<uint8_t>(n_all);

        put_u8(txBuf_, TELEMETRY_BIN_VERSION);
        put_u16(txBuf_, seq_++);
        put_u32(txBuf_, now_ms);
        put_u8(txBuf_, count);

        uint8_t emittedSections = 0;
        uint8_t droppedSections = 0;
        for (size_t i = 0; i < count; ++i) {
            auto& p = binProviders_[i];
            sectionBuf_.clear();
            p.fn(sectionBuf_);
            if (sectionBuf_.size() > 0xFFFF) {
                DBG_PRINTF("[TelemetryModule] section %u too large (%u), skipping\n", (unsigned)p.section_id, (unsigned)sectionBuf_.size());
                ++droppedSections;
                continue;
            }
            put_u8(txBuf_, p.section_id);
            put_u16(txBuf_, static_cast<uint16_t>(sectionBuf_.size()));
            txBuf_.insert(txBuf_.end(), sectionBuf_.begin(), sectionBuf_.end());
            ++emittedSections;
        }
        txBuf_[7] = emittedSections;

        Event evt;
        evt.type = EventType::BIN_MESSAGE_TX;
        evt.timestamp_ms = now_ms;
        evt.payload.bin = txBuf_;
        recordPacket(now_ms, txBuf_.size(), emittedSections, droppedSections);
        bus_.publish(evt);
    }

    if (jsonEnabled_ && !jsonProviders_.empty()) {
        using namespace ArduinoJson;
        jsonDoc_.clear();
        jsonDoc_["src"] = "mcu";
        jsonDoc_["type"] = "TELEMETRY";
        jsonDoc_["ts_ms"] = now_ms;
        JsonObject data = jsonDoc_["data"].to<JsonObject>();
        for (auto& p : jsonProviders_) {
            JsonObject node = data[p.name.c_str()].to<JsonObject>();
            p.fn(node);
        }
        std::string out;
        serializeJson(jsonDoc_, out);
        Event evt;
        evt.type = EventType::JSON_MESSAGE_TX;
        evt.timestamp_ms = now_ms;
        evt.payload.json = std::move(out);
        bus_.publish(evt);
    }
}
