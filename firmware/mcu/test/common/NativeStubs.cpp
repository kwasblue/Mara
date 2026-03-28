// test/common/NativeStubs.cpp
// Provides minimal native-only definitions for MCU-only code paths so unit tests can link.

#ifdef PIO_UNIT_TESTING

#include <array>
#include <cstdint>
#include <string>
#include <vector>

// -------------------- Time stubs for native tests --------------------
// These are used by Clock.cpp and arduino_stubs.h
extern "C" {
    uint32_t __test_millis = 0;
    uint32_t __test_micros = 0;
}

// -------------------- Clock stubs --------------------
#include "core/Clock.h"

namespace mara {

uint32_t SystemClock::millis() const { return __test_millis; }
uint32_t SystemClock::micros() const { return __test_micros; }

static SystemClock g_systemClock;

SystemClock& getSystemClock() { return g_systemClock; }

} // namespace mara

// Include project headers using include/ as the root (PlatformIO adds include/ to the include path)
#include "command/ModeManager.h"
#include "module/LoggingModule.h"
#include "module/TelemetryModule.h"
#include "sensor/EncoderManager.h"
#include "motor/MotionController.h"

// -------------------- maraModeToString --------------------
// Declared somewhere in your project (ModeManager/State), but implementation lives in MCU build.
// Provide a native definition so CommandHandler can link.
const char* maraModeToString(MaraMode mode) {
    switch (mode) {
        case MaraMode::BOOT:         return "BOOT";
        case MaraMode::DISCONNECTED: return "DISCONNECTED";
        case MaraMode::IDLE:         return "IDLE";
        case MaraMode::ARMED:        return "ARMED";
        case MaraMode::ACTIVE:       return "ACTIVE";
        case MaraMode::ESTOPPED:     return "ESTOPPED";
        default:                     return "UNKNOWN";
    }
}

// -------------------- ModeManager stubs (with working state machine) --------------------
void ModeManager::begin() {
    mode_ = MaraMode::IDLE;
}

void ModeManager::arm() {
    if (mode_ == MaraMode::IDLE) {
        mode_ = MaraMode::ARMED;
    }
}

void ModeManager::disarm() {
    if (mode_ == MaraMode::ARMED || mode_ == MaraMode::ACTIVE) {
        mode_ = MaraMode::IDLE;
    }
}

void ModeManager::activate() {
    if (mode_ == MaraMode::ARMED) {
        mode_ = MaraMode::ACTIVE;
    }
}

void ModeManager::deactivate() {
    if (mode_ == MaraMode::ACTIVE) {
        mode_ = MaraMode::ARMED;
    }
}

void ModeManager::estop() {
    mode_ = MaraMode::ESTOPPED;
}

bool ModeManager::clearEstop() {
    if (mode_ == MaraMode::ESTOPPED) {
        mode_ = MaraMode::IDLE;
        return true;
    }
    return false;
}

void ModeManager::update(uint32_t /*now_ms*/) {}
void ModeManager::onHostHeartbeat(uint32_t /*ms*/) {}
void ModeManager::onMotionCommand(uint32_t /*ms*/, float /*vx*/, float /*omega*/) {}

bool ModeManager::validateVelocity(float vx, float omega, float& outVx, float& outOmega) {
    // Clamp to configured limits
    float maxLin = cfg_.max_linear_vel;
    float maxAng = cfg_.max_angular_vel;

    if (vx > maxLin) vx = maxLin;
    if (vx < -maxLin) vx = -maxLin;
    if (omega > maxAng) omega = maxAng;
    if (omega < -maxAng) omega = -maxAng;

    outVx = vx;
    outOmega = omega;
    return true;
}

// -------------------- LoggingModule stubs --------------------
// Your linker error mentions LoggingModule::s_instance and setLogLevel().
LoggingModule* LoggingModule::s_instance = nullptr;

void LoggingModule::setLogLevel(const char* /*level*/) {}

// -------------------- TelemetryModule stubs --------------------
namespace {
EventBus* g_telem_bus = nullptr;
std::vector<TelemetryModule::BinProviderFn> g_telem_bin_providers;
uint32_t g_telem_interval_ms = 0;
bool g_telem_binary_enabled = true;
bool g_telem_json_enabled = false;
uint16_t g_telem_seq = 0;
uint32_t g_telem_last_tick_ms = 0;
std::array<TelemetryModule::PacketRecord, 32> g_telem_history{};
size_t g_telem_history_head = 0;
size_t g_telem_history_count = 0;
TelemetryModule::PacketStats g_telem_stats{};
}

TelemetryModule::TelemetryModule(EventBus& bus)
    : bus_(bus) {
    g_telem_bus = &bus;
    g_telem_bin_providers.clear();
    g_telem_interval_ms = 0;
    g_telem_binary_enabled = true;
    g_telem_json_enabled = false;
    g_telem_seq = 0;
    g_telem_last_tick_ms = 0;
    g_telem_history_head = 0;
    g_telem_history_count = 0;
    g_telem_stats = {};
}

void TelemetryModule::setup() {}
void TelemetryModule::setInterval(uint32_t ms) { g_telem_interval_ms = ms; g_telem_last_tick_ms = 0; }
void TelemetryModule::setBinaryEnabled(bool en) { g_telem_binary_enabled = en; }
void TelemetryModule::setJsonEnabled(bool en) { g_telem_json_enabled = en; }
void TelemetryModule::registerProvider(const char* /*name*/, JsonProviderFn /*fn*/) {}
void TelemetryModule::registerBinProvider(uint8_t /*section_id*/, BinProviderFn fn) { g_telem_bin_providers.push_back(std::move(fn)); }
const TelemetryModule::PacketRecord* TelemetryModule::packetHistory(size_t& count, size_t& head) const { count = g_telem_history_count; head = g_telem_history_head; return g_telem_history.data(); }
void TelemetryModule::recordPacket(uint32_t now_ms, size_t bytes, uint8_t sectionCount, uint8_t droppedSections) { auto& r = g_telem_history[g_telem_history_head]; r.ts_ms = now_ms; r.bytes = static_cast<uint16_t>(bytes); r.sections = sectionCount; r.dropped_sections = droppedSections; g_telem_history_head = (g_telem_history_head + 1) % g_telem_history.size(); if (g_telem_history_count < g_telem_history.size()) ++g_telem_history_count; g_telem_stats.sent_packets++; g_telem_stats.sent_bytes += static_cast<uint32_t>(bytes); g_telem_stats.last_packet_bytes = static_cast<uint16_t>(bytes); if (bytes > g_telem_stats.max_packet_bytes) g_telem_stats.max_packet_bytes = static_cast<uint16_t>(bytes); g_telem_stats.last_section_count = sectionCount; if (sectionCount > g_telem_stats.max_section_count) g_telem_stats.max_section_count = sectionCount; g_telem_stats.dropped_sections += droppedSections; g_telem_stats.buffered_packets = static_cast<uint16_t>(g_telem_history_count); g_telem_stats.last_emit_ms = now_ms; }
void TelemetryModule::loop(uint32_t now_ms) { if (!g_telem_bus || !g_telem_binary_enabled || g_telem_interval_ms == 0) return; if ((now_ms - g_telem_last_tick_ms) < g_telem_interval_ms) return; g_telem_last_tick_ms = now_ms; std::vector<uint8_t> payload; payload.push_back(1); payload.push_back(static_cast<uint8_t>(g_telem_seq & 0xFF)); payload.push_back(static_cast<uint8_t>((g_telem_seq >> 8) & 0xFF)); g_telem_seq++; payload.push_back(static_cast<uint8_t>(now_ms & 0xFF)); payload.push_back(static_cast<uint8_t>((now_ms >> 8) & 0xFF)); payload.push_back(static_cast<uint8_t>((now_ms >> 16) & 0xFF)); payload.push_back(static_cast<uint8_t>((now_ms >> 24) & 0xFF)); payload.push_back(static_cast<uint8_t>(g_telem_bin_providers.size())); uint8_t sections = 0; for (size_t i = 0; i < g_telem_bin_providers.size(); ++i) { std::vector<uint8_t> body; g_telem_bin_providers[i](body); payload.push_back(static_cast<uint8_t>(i + 1)); payload.push_back(static_cast<uint8_t>(body.size() & 0xFF)); payload.push_back(static_cast<uint8_t>((body.size() >> 8) & 0xFF)); payload.insert(payload.end(), body.begin(), body.end()); sections++; } payload[7] = sections; Event evt{}; evt.type = EventType::BIN_MESSAGE_TX; evt.timestamp_ms = now_ms; evt.payload.bin = payload; recordPacket(now_ms, payload.size(), sections, 0); g_telem_bus->publish(evt); }

// -------------------- MotionController stubs --------------------
// Your linker error includes MotionController constructor + stop + setServoTarget + moveStepperRelative.
MotionController::MotionController(
    DcMotorManager& motors,
    uint8_t /*leftMotorId*/,
    uint8_t /*rightMotorId*/,
    float /*wheelBase*/,
    float /*maxLinear*/,
    float /*maxAngular*/,
    ServoManager* /*servoMgr*/,
    StepperManager* /*stepperMgr*/
) : motors_(motors) {}

void MotionController::setVelocity(float /*vx*/, float /*omega*/) {}
void MotionController::stop() {}

void MotionController::setServoTarget(uint8_t /*servoId*/, float /*angleDeg*/, uint32_t /*durationMs*/) {}
void MotionController::moveStepperRelative(int /*motorId*/, int /*steps*/, float /*speedStepsPerSec*/) {}

// -------------------- SignalBus stubs --------------------
#include "control/SignalBus.h"

#if HAS_SIGNAL_BUS
bool SignalBus::set(uint16_t /*id*/, float /*v*/, uint32_t /*now_ms*/) {
    return true;
}

bool SignalBus::get(uint16_t /*id*/, float& /*out*/) const {
    return false;
}
#endif

#endif // PIO_UNIT_TESTING
