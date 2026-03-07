// test/common/NativeStubs.cpp
// Provides minimal native-only definitions for MCU-only code paths so unit tests can link.

#ifdef PIO_UNIT_TESTING

#include <cstdint>
#include <string>

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
        case MaraMode::DISARMED:  return "DISARMED";
        case MaraMode::ARMED:     return "ARMED";
        case MaraMode::ACTIVE:    return "ACTIVE";
        case MaraMode::ESTOP:     return "ESTOP";
        default:                   return "UNKNOWN";
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

// -------------------- EncoderManager stubs --------------------
// Your linker error lists EncoderManager ctor, attach/reset/getCount.
EncoderManager::EncoderManager() {}

bool EncoderManager::attach(uint8_t /*id*/, uint8_t /*pinA*/, uint8_t /*pinB*/) {
    return true;
}

void EncoderManager::reset(uint8_t /*id*/) {}

int32_t EncoderManager::getCount(uint8_t /*id*/) const {
    return 0;
}

// -------------------- TelemetryModule stubs --------------------
TelemetryModule::TelemetryModule(EventBus& /*bus*/) {}
TelemetryModule::~TelemetryModule() = default;

void TelemetryModule::setInterval(uint32_t /*ms*/) {}

// If TelemetryModule overrides handleEvent out-of-line in the real build,
// define it here too so the vtable is complete.
void TelemetryModule::handleEvent(const Event& /*evt*/) {}

// -------------------- MotionController stubs --------------------
// Your linker error includes MotionController constructor + stop + setServoTarget + moveStepperRelative.
MotionController::MotionController(
    DcMotorManager& /*motors*/,
    uint8_t /*leftMotorId*/,
    uint8_t /*rightMotorId*/,
    float /*wheelBase*/,
    float /*maxLinear*/,
    float /*maxAngular*/,
    ServoManager* /*servoMgr*/,
    StepperManager* /*stepperMgr*/
) {}

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
