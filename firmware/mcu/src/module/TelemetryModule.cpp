// modules/TelemetryModule.cpp
#include "module/TelemetryModule.h"
#include "core/Debug.h"

#include <ArduinoJson.h>

// -----------------------------
// Binary payload format (little-endian) — inside Protocol::MSG_TELEMETRY_BIN
//
// payload:
//   u8   version (=1)
//   u16  seq
//   u32  ts_ms
//   u8   section_count
//   repeat section_count times:
//     u8   section_id
//     u16  section_len
//     u8[] section_bytes
// -----------------------------
static constexpr uint8_t TELEMETRY_BIN_VERSION = 1;

TelemetryModule::TelemetryModule(EventBus& bus)
    : bus_(bus)
{
    txBuf_.reserve(256);
    sectionBuf_.reserve(128);
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

// -----------------------------
// Provider registration
// -----------------------------
void TelemetryModule::registerProvider(const char* name, JsonProviderFn fn) {
    if (!name || !fn) return;

    JsonProvider p;
    p.name = name;
    p.fn   = std::move(fn);
    jsonProviders_.push_back(std::move(p));

    DBG_PRINTF("[TelemetryModule] registered JSON provider '%s'\n", name);
}

void TelemetryModule::registerBinProvider(uint8_t section_id, BinProviderFn fn) {
    if (!fn) return;

    // Reserve 0 as invalid if you want
    if (section_id == 0) {
        DBG_PRINTLN("[TelemetryModule] refusing BIN provider with section_id=0");
        return;
    }

    // Replace if already registered (prevents duplicates)
    for (auto& p : binProviders_) {
        if (p.section_id == section_id) {
            p.fn = std::move(fn);
            DBG_PRINTF("[TelemetryModule] updated BIN provider id=%u\n", (unsigned)section_id);
            return;
        }
    }

    BinProvider p;
    p.section_id = section_id;
    p.fn         = std::move(fn);
    binProviders_.push_back(std::move(p));

    DBG_PRINTF("[TelemetryModule] registered BIN provider id=%u\n", (unsigned)section_id);
}

// -----------------------------
// Output toggles
// -----------------------------
void TelemetryModule::setBinaryEnabled(bool en) { binaryEnabled_ = en; }
void TelemetryModule::setJsonEnabled(bool en)   { jsonEnabled_   = en; }

// -----------------------------
// Packing helpers (LE)
// -----------------------------
void TelemetryModule::put_u8(std::vector<uint8_t>& b, uint8_t v) {
    b.push_back(v);
}

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

// -----------------------------
// Telemetry send
// -----------------------------
void TelemetryModule::sendTelemetry(uint32_t now_ms) {
    // ---------- Binary telemetry ----------
    if (binaryEnabled_ && !binProviders_.empty()) {
        txBuf_.clear();

        // cap count to u8
        const size_t n_all = binProviders_.size();
        const uint8_t count = (n_all > 255) ? 255 : static_cast<uint8_t>(n_all);

        // header
        put_u8 (txBuf_, TELEMETRY_BIN_VERSION);
        put_u16(txBuf_, seq_++);   // seq
        put_u32(txBuf_, now_ms);   // ts_ms
        put_u8 (txBuf_, count);    // section_count

        // sections
        for (size_t i = 0; i < count; ++i) {
            auto& p = binProviders_[i];

            sectionBuf_.clear();
            p.fn(sectionBuf_);

            if (sectionBuf_.size() > 0xFFFF) {
                DBG_PRINTF("[TelemetryModule] section %u too large (%u), skipping\n",
                           (unsigned)p.section_id, (unsigned)sectionBuf_.size());
                continue;
            }

            put_u8 (txBuf_, p.section_id);
            put_u16(txBuf_, static_cast<uint16_t>(sectionBuf_.size()));
            txBuf_.insert(txBuf_.end(), sectionBuf_.begin(), sectionBuf_.end());
        }

        Event evt;
        evt.type         = EventType::BIN_MESSAGE_TX;
        evt.timestamp_ms = now_ms;
        evt.payload.bin  = txBuf_;   // copy (safe because txBuf_ is reused)

        bus_.publish(evt);
    }

    // ---------- JSON telemetry (optional) ----------
    if (jsonEnabled_ && !jsonProviders_.empty()) {
        using namespace ArduinoJson;

        // Reuse member document to avoid heap allocation per emit
        jsonDoc_.clear();
        jsonDoc_["src"]   = "mcu";
        jsonDoc_["type"]  = "TELEMETRY";
        jsonDoc_["ts_ms"] = now_ms;

        JsonObject data = jsonDoc_["data"].to<JsonObject>();

        for (auto& p : jsonProviders_) {
            JsonObject node = data[p.name.c_str()].to<JsonObject>();
            p.fn(node);
        }

        std::string out;
        serializeJson(jsonDoc_, out);

        Event evt;
        evt.type         = EventType::JSON_MESSAGE_TX;
        evt.timestamp_ms = now_ms;
        evt.payload.json = std::move(out);

        bus_.publish(evt);
    }
}
