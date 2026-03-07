// test/test_command_handler_ack/native_stubs.cpp
// Stubs for native testing of CommandHandler ACK logic
// These stubs allow the test to link without pulling in the full firmware

#include "command/ModeManager.h"
#include "command/decoders/ControlDecoders.h"
#include "command/decoders/ObserverDecoders.h"
#include "control/ControlKernel.h"
#include "control/Observer.h"
#include "control/SignalBus.h"
#include "core/LoopRates.h"
#include "core/Clock.h"
#include "core/IntentBuffer.h"
#include "module/LoggingModule.h"
#include "sensor/EncoderManager.h"
#include "module/TelemetryModule.h"
#include "motor/MotionController.h"

// ============================================================================
// Time stubs
// ============================================================================
extern "C" {
    uint32_t __test_millis = 0;
    uint32_t __test_micros = 0;
}

namespace mara {
uint32_t SystemClock::millis() const { return __test_millis; }
uint32_t SystemClock::micros() const { return __test_micros; }
static SystemClock g_systemClock;
SystemClock& getSystemClock() { return g_systemClock; }
} // namespace mara

// ============================================================================
// LoopRates
// ============================================================================
static LoopRates g_loopRates{100, 50, 10};

LoopRates& getLoopRates() {
    return g_loopRates;
}

// ============================================================================
// ModeManager stubs
// ============================================================================
const char* maraModeToString(MaraMode mode) {
    switch (mode) {
        case MaraMode::BOOT:         return "BOOT";
        case MaraMode::DISCONNECTED: return "DISCONNECTED";
        case MaraMode::IDLE:         return "IDLE";
        case MaraMode::ARMED:        return "ARMED";
        case MaraMode::ACTIVE:       return "ACTIVE";
        case MaraMode::ESTOPPED:     return "ESTOPPED";
        default:                      return "UNKNOWN";
    }
}

void ModeManager::onHostHeartbeat(uint32_t) {}
void ModeManager::onMotionCommand(uint32_t, float, float) {}

bool ModeManager::validateVelocity(float vx, float omega, float& outVx, float& outOmega) {
    outVx = vx;
    outOmega = omega;
    return true;
}

void ModeManager::arm() { mode_ = MaraMode::ARMED; }
void ModeManager::activate() { mode_ = MaraMode::ACTIVE; }
void ModeManager::deactivate() { mode_ = MaraMode::ARMED; }
void ModeManager::disarm() { mode_ = MaraMode::IDLE; }
void ModeManager::estop() { mode_ = MaraMode::ESTOPPED; }
bool ModeManager::clearEstop() { mode_ = MaraMode::IDLE; return true; }

// ============================================================================
// SignalBus stubs
// ============================================================================
int SignalBus::indexOf_(uint16_t id) const {
    for (size_t i = 0; i < signals_.size(); ++i) {
        if (signals_[i].id == id) return static_cast<int>(i);
    }
    return -1;
}

bool SignalBus::define(uint16_t id, const char* name, Kind kind, float initial) {
    // Idempotent: update if exists
    for (auto& s : signals_) {
        if (s.id == id) {
            s.kind = kind;
            s.value = initial;
            s.ts_ms = 0;
            if (name && name[0] != '\0') {
                strncpy(s.name, name, NAME_MAX_LEN);
                s.name[NAME_MAX_LEN] = '\0';
            }
            return true;
        }
    }
    SignalDef def;
    def.id = id;
    def.kind = kind;
    def.value = initial;
    def.ts_ms = 0;
    if (name) {
        strncpy(def.name, name, NAME_MAX_LEN);
        def.name[NAME_MAX_LEN] = '\0';
    } else {
        def.name[0] = '\0';
    }
    signals_.push_back(def);
    return true;
}

bool SignalBus::exists(uint16_t id) const {
    return indexOf_(id) >= 0;
}

bool SignalBus::set(uint16_t id, float v, uint32_t now_ms) {
    int idx = indexOf_(id);
    if (idx < 0) return false;
    signals_[idx].value = v;
    signals_[idx].ts_ms = now_ms;
    return true;
}

bool SignalBus::get(uint16_t id, float& out) const {
    int idx = indexOf_(id);
    if (idx < 0) return false;
    out = signals_[idx].value;
    return true;
}

bool SignalBus::getTimestamp(uint16_t id, uint32_t& out) const {
    int idx = indexOf_(id);
    if (idx < 0) return false;
    out = signals_[idx].ts_ms;
    return true;
}

bool SignalBus::remove(uint16_t id) {
    int idx = indexOf_(id);
    if (idx < 0) return false;
    signals_.erase(signals_.begin() + idx);
    return true;
}

const SignalBus::SignalDef* SignalBus::find(uint16_t id) const {
    int idx = indexOf_(id);
    if (idx < 0) return nullptr;
    return &signals_[idx];
}

// ============================================================================
// ControlKernel stubs
// ============================================================================
bool ControlKernel::configureSlot(const SlotConfig& cfg, const char* type) {
    (void)cfg; (void)type;
    return true;
}

bool ControlKernel::enableSlot(uint8_t slot, bool enable) {
    (void)slot; (void)enable;
    return true;
}

bool ControlKernel::resetSlot(uint8_t slot) {
    (void)slot;
    return true;
}

bool ControlKernel::setParam(uint8_t slot, const char* key, float value) {
    (void)slot; (void)key; (void)value;
    return true;
}

bool ControlKernel::getParam(uint8_t slot, const char* key, float& value) const {
    (void)slot; (void)key;
    value = 0.0f;
    return true;
}

bool ControlKernel::setParamArray(uint8_t slot, const char* key, const float* values, size_t len) {
    (void)slot; (void)key; (void)values; (void)len;
    return true;
}

SlotConfig ControlKernel::getConfig(uint8_t slot) const {
    (void)slot;
    SlotConfig cfg{};
    return cfg;
}

SlotStatus ControlKernel::getStatus(uint8_t slot) const {
    (void)slot;
    SlotStatus st{};
    st.ok = true;
    return st;
}

void ControlKernel::step(uint32_t now_ms, float dt_s, SignalBus& signals, bool is_armed, bool is_active) {
    (void)now_ms; (void)dt_s; (void)signals; (void)is_armed; (void)is_active;
}

void ControlKernel::resetAll() {}
void ControlKernel::disableAll() {}

// ============================================================================
// LuenbergerObserver stubs
// ============================================================================
void LuenbergerObserver::configure(uint8_t num_states, uint8_t num_inputs, uint8_t num_outputs) {
    num_states_ = num_states;
    num_inputs_ = num_inputs;
    num_outputs_ = num_outputs;
    initialized_ = true;
}

void LuenbergerObserver::update(const float* u, const float* y, float dt, float* x_hat_out) {
    (void)u; (void)y; (void)dt;
    if (x_hat_out) {
        for (uint8_t i = 0; i < num_states_; ++i) {
            x_hat_out[i] = x_hat_[i];
        }
    }
}

void LuenbergerObserver::reset() {
    for (uint8_t i = 0; i < MAX_STATES; ++i) x_hat_[i] = 0.0f;
}

void LuenbergerObserver::initState(const float* x0) {
    if (x0) {
        for (uint8_t i = 0; i < num_states_; ++i) x_hat_[i] = x0[i];
    }
}

void LuenbergerObserver::setState(uint8_t idx, float value) {
    if (idx < MAX_STATES) x_hat_[idx] = value;
}

float LuenbergerObserver::getState(uint8_t idx) const {
    if (idx < MAX_STATES) return x_hat_[idx];
    return 0.0f;
}

bool LuenbergerObserver::setA(const float* A, size_t len) { (void)A; (void)len; return true; }
bool LuenbergerObserver::setB(const float* B, size_t len) { (void)B; (void)len; return true; }
bool LuenbergerObserver::setC(const float* C, size_t len) { (void)C; (void)len; return true; }
bool LuenbergerObserver::setL(const float* L, size_t len) { (void)L; (void)len; return true; }

bool LuenbergerObserver::setParam(const char* key, float value) {
    (void)key; (void)value;
    return true;
}

bool LuenbergerObserver::setParamArray(const char* key, const float* values, size_t len) {
    (void)key; (void)values; (void)len;
    return true;
}

// ============================================================================
// ObserverManager stubs
// ============================================================================
bool ObserverManager::configure(uint8_t slot, const ObserverConfig& config, uint16_t rate_hz) {
    if (slot >= MAX_SLOTS) return false;
    slots_[slot].config = config;
    slots_[slot].rate_hz = rate_hz;
    slots_[slot].configured = true;
    slots_[slot].observer.configure(config.num_states, config.num_inputs, config.num_outputs);
    return true;
}

bool ObserverManager::enable(uint8_t slot, bool en) {
    if (slot >= MAX_SLOTS || !slots_[slot].configured) return false;
    slots_[slot].enabled = en;
    return true;
}

bool ObserverManager::reset(uint8_t slot) {
    if (slot >= MAX_SLOTS) return false;
    slots_[slot].observer.reset();
    return true;
}

bool ObserverManager::setParam(uint8_t slot, const char* key, float value) {
    if (slot >= MAX_SLOTS) return false;
    return slots_[slot].observer.setParam(key, value);
}

bool ObserverManager::setParamArray(uint8_t slot, const char* key, const float* values, size_t len) {
    if (slot >= MAX_SLOTS) return false;
    return slots_[slot].observer.setParamArray(key, values, len);
}

void ObserverManager::step(uint32_t now_ms, float dt_s, SignalBus& signals) {
    (void)now_ms; (void)dt_s; (void)signals;
}

LuenbergerObserver* ObserverManager::getObserver(uint8_t slot) {
    if (slot >= MAX_SLOTS) return nullptr;
    return &slots_[slot].observer;
}

const ObserverManager::Slot& ObserverManager::getSlot(uint8_t slot) const {
    static Slot empty{};
    if (slot >= MAX_SLOTS) return empty;
    return slots_[slot];
}

void ObserverManager::resetAll() {
    for (auto& s : slots_) {
        s.observer.reset();
    }
}

void ObserverManager::disableAll() {
    for (auto& s : slots_) {
        s.enabled = false;
    }
}

// ============================================================================
// LoggingModule stub
// ============================================================================
LoggingModule* LoggingModule::s_instance = nullptr;

void LoggingModule::setLogLevel(const char* level) {
    (void)level;
}

// ============================================================================
// EncoderManager stubs - REMOVED: Now provided by header when HAS_ENCODER=0
// ============================================================================

// ============================================================================
// TelemetryModule stubs
// ============================================================================
TelemetryModule::TelemetryModule(EventBus& bus)
    : bus_(bus), intervalMs_(100), binaryEnabled_(true), jsonEnabled_(false) {}

void TelemetryModule::setup() {}
void TelemetryModule::loop(uint32_t now_ms) { (void)now_ms; }

void TelemetryModule::registerProvider(const char* name, JsonProviderFn fn) {
    (void)name; (void)fn;
}

void TelemetryModule::registerBinProvider(uint8_t section_id, BinProviderFn fn) {
    (void)section_id; (void)fn;
}

void TelemetryModule::setInterval(uint32_t intervalMs) {
    intervalMs_ = intervalMs;
}

void TelemetryModule::setBinaryEnabled(bool en) { binaryEnabled_ = en; }
void TelemetryModule::setJsonEnabled(bool en) { jsonEnabled_ = en; }

// ============================================================================
// MotionController stubs
// ============================================================================
MotionController::MotionController(
    DcMotorManager& motors,
    uint8_t leftMotorId,
    uint8_t rightMotorId,
    float wheelBase,
    float maxLinear,
    float maxAngular,
    ServoManager* servoMgr,
    StepperManager* stepperMgr)
    : motors_(motors)
    , servoMgr_(servoMgr)
    , stepperMgr_(stepperMgr)
    , leftId_(leftMotorId)
    , rightId_(rightMotorId)
    , wheelBase_(wheelBase)
    , maxLinear_(maxLinear)
    , maxAngular_(maxAngular)
    , baseEnabled_(false)
{}

void MotionController::setVelocity(float vx, float omega) {
    vxRef_ = vx;
    omegaRef_ = omega;
}

void MotionController::stop() {
    vxRef_ = 0;
    omegaRef_ = 0;
}

float MotionController::vx() const { return vxRef_; }
float MotionController::omega() const { return omegaRef_; }

void MotionController::setAccelLimits(float maxLinAccel, float maxAngAccel) {
    (void)maxLinAccel; (void)maxAngAccel;
}

void MotionController::setBaseEnabled(bool enabled) {
    baseEnabled_ = enabled;
}

void MotionController::setServoTarget(uint8_t servoId, float angleDeg, uint32_t durationMs) {
    (void)servoId; (void)angleDeg; (void)durationMs;
}

void MotionController::setServoImmediate(uint8_t servoId, float angleDeg) {
    (void)servoId; (void)angleDeg;
}

void MotionController::moveStepperRelative(int motorId, int steps, float speedStepsPerSec) {
    (void)motorId; (void)steps; (void)speedStepsPerSec;
}

void MotionController::enableStepper(int motorId, bool enabled) {
    (void)motorId; (void)enabled;
}

void MotionController::update(float dt) {
    (void)dt;
}

// ============================================================================
// IntentBuffer stubs
// ============================================================================
namespace mara {

void IntentBuffer::setVelocityIntent(float vx, float omega, uint32_t now_ms) {
    velocity_.vx = vx;
    velocity_.omega = omega;
    velocity_.timestamp_ms = now_ms;
    velocity_.pending = true;
}

bool IntentBuffer::consumeVelocityIntent(VelocityIntent& out) {
    if (!velocity_.pending) return false;
    out = velocity_;
    velocity_.pending = false;
    return true;
}

void IntentBuffer::setServoIntent(uint8_t id, float angle, uint32_t dur_ms, uint32_t now_ms) {
    if (id >= MAX_SERVO_INTENTS) return;
    servos_[id].id = id;
    servos_[id].angle_deg = angle;
    servos_[id].duration_ms = dur_ms;
    servos_[id].timestamp_ms = now_ms;
    servos_[id].pending = true;
}

bool IntentBuffer::consumeServoIntent(uint8_t id, ServoIntent& out) {
    if (id >= MAX_SERVO_INTENTS) return false;
    if (!servos_[id].pending) return false;
    out = servos_[id];
    servos_[id].pending = false;
    return true;
}

void IntentBuffer::setDcMotorIntent(uint8_t id, float speed, uint32_t now_ms) {
    if (id >= MAX_DC_MOTOR_INTENTS) return;
    dcMotors_[id].id = id;
    dcMotors_[id].speed = speed;
    dcMotors_[id].timestamp_ms = now_ms;
    dcMotors_[id].pending = true;
}

bool IntentBuffer::consumeDcMotorIntent(uint8_t id, DcMotorIntent& out) {
    if (id >= MAX_DC_MOTOR_INTENTS) return false;
    if (!dcMotors_[id].pending) return false;
    out = dcMotors_[id];
    dcMotors_[id].pending = false;
    return true;
}

void IntentBuffer::setStepperIntent(int id, int steps, float speed, uint32_t now_ms) {
    if (id < 0 || id >= MAX_STEPPER_INTENTS) return;
    steppers_[id].motor_id = id;
    steppers_[id].steps = steps;
    steppers_[id].speed_steps_s = speed;
    steppers_[id].timestamp_ms = now_ms;
    steppers_[id].pending = true;
}

bool IntentBuffer::consumeStepperIntent(int id, StepperIntent& out) {
    if (id < 0 || id >= MAX_STEPPER_INTENTS) return false;
    if (!steppers_[id].pending) return false;
    out = steppers_[id];
    steppers_[id].pending = false;
    return true;
}

void IntentBuffer::queueSignalIntent(uint16_t id, float value, uint32_t now_ms) {
    uint8_t next = (signalHead_ + 1) % MAX_SIGNAL_INTENTS;
    if (next == signalTail_) {
        signalTail_ = (signalTail_ + 1) % MAX_SIGNAL_INTENTS;
    }
    signalRing_[signalHead_].id = id;
    signalRing_[signalHead_].value = value;
    signalRing_[signalHead_].timestamp_ms = now_ms;
    signalHead_ = next;
}

bool IntentBuffer::consumeSignalIntent(SignalIntent& out) {
    if (signalHead_ == signalTail_) return false;
    out = signalRing_[signalTail_];
    signalTail_ = (signalTail_ + 1) % MAX_SIGNAL_INTENTS;
    return true;
}

uint8_t IntentBuffer::pendingSignalCount() const {
    if (signalHead_ >= signalTail_) {
        return signalHead_ - signalTail_;
    }
    return MAX_SIGNAL_INTENTS - signalTail_ + signalHead_;
}

void IntentBuffer::clearAll() {
    velocity_.pending = false;
    for (uint8_t i = 0; i < MAX_SERVO_INTENTS; ++i) servos_[i].pending = false;
    for (uint8_t i = 0; i < MAX_DC_MOTOR_INTENTS; ++i) dcMotors_[i].pending = false;
    for (uint8_t i = 0; i < MAX_STEPPER_INTENTS; ++i) steppers_[i].pending = false;
    signalHead_ = 0;
    signalTail_ = 0;
}

} // namespace mara

// ============================================================================
// Control/Observer Decoder stubs
// ============================================================================
namespace mara {
namespace cmd {

size_t extractUint16Array(JsonArrayConst arr, uint16_t* out, size_t maxLen) {
    if (!arr || !out || maxLen == 0) return 0;
    size_t count = 0;
    for (size_t i = 0; i < arr.size() && i < maxLen; i++) {
        out[i] = arr[i].as<uint16_t>();
        count++;
    }
    return count;
}

size_t extractFloatArray(JsonArrayConst arr, float* out, size_t maxLen) {
    if (!arr || !out || maxLen == 0) return 0;
    size_t count = 0;
    for (size_t i = 0; i < arr.size() && i < maxLen; i++) {
        out[i] = arr[i].as<float>();
        count++;
    }
    return count;
}

SlotConfigResult decodeSlotConfig(JsonVariantConst payload) {
    SlotConfigResult result;
    result.config.slot = payload["slot"] | 0;
    result.config.rate_hz = payload["rate_hz"] | 100;
    result.config.require_armed = payload["require_armed"] | true;
    result.config.require_active = payload["require_active"] | true;
    result.controllerType = payload["controller_type"] | "PID";

    if (strcmp(result.controllerType, "STATE_SPACE") == 0 ||
        strcmp(result.controllerType, "SS") == 0) {
        result.config.ss_io.num_states = payload["num_states"] | 2;
        result.config.ss_io.num_inputs = payload["num_inputs"] | 1;
        JsonArrayConst state_ids = payload["state_ids"].as<JsonArrayConst>();
        if (state_ids) extractUint16Array(state_ids, result.config.ss_io.state_ids, StateSpaceIO::MAX_STATES);
        JsonArrayConst ref_ids = payload["ref_ids"].as<JsonArrayConst>();
        if (ref_ids) extractUint16Array(ref_ids, result.config.ss_io.ref_ids, StateSpaceIO::MAX_STATES);
        JsonArrayConst out_ids = payload["output_ids"].as<JsonArrayConst>();
        if (out_ids) extractUint16Array(out_ids, result.config.ss_io.output_ids, StateSpaceIO::MAX_INPUTS);
    } else {
        result.config.io.ref_id = payload["ref_id"] | 0;
        result.config.io.meas_id = payload["meas_id"] | 0;
        result.config.io.out_id = payload["out_id"] | 0;
    }
    result.valid = true;
    return result;
}

SignalDefResult decodeSignalDef(JsonVariantConst payload) {
    SignalDefResult result;
    if (payload["id"].isNull() || payload["name"].isNull() || payload["kind"].isNull()) {
        result.error = "missing_fields";
        return result;
    }
    result.id = payload["id"].as<uint16_t>();
    const char* name = payload["name"].as<const char*>();
    if (name) {
        strncpy(result.name, name, SignalBus::NAME_MAX_LEN);
        result.name[SignalBus::NAME_MAX_LEN] = '\0';
    }
    const char* kindStr = payload["signal_kind"] | payload["kind"] | "REF";
    result.kind = signalKindFromString(kindStr);
    result.initial = payload["initial"] | 0.0f;
    result.valid = true;
    return result;
}

ObserverConfigResult decodeObserverConfig(JsonVariantConst payload) {
    ObserverConfigResult result;
    result.slot = payload["slot"] | 0;
    result.rate_hz = payload["rate_hz"] | 200;
    result.config.num_states = payload["num_states"] | 2;
    result.config.num_inputs = payload["num_inputs"] | 1;
    result.config.num_outputs = payload["num_outputs"] | 1;

    JsonArrayConst input_ids = payload["input_ids"].as<JsonArrayConst>();
    if (input_ids) extractUint16Array(input_ids, result.config.input_ids, ObserverConfig::MAX_INPUTS);
    JsonArrayConst output_ids = payload["output_ids"].as<JsonArrayConst>();
    if (output_ids) extractUint16Array(output_ids, result.config.output_ids, ObserverConfig::MAX_OUTPUTS);
    JsonArrayConst estimate_ids = payload["estimate_ids"].as<JsonArrayConst>();
    if (estimate_ids) extractUint16Array(estimate_ids, result.config.estimate_ids, ObserverConfig::MAX_STATES);

    result.valid = true;
    return result;
}

} // namespace cmd
} // namespace mara