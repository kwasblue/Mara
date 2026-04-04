// src/managers/EncoderManager.cpp
#include "config/FeatureFlags.h"

#if HAS_ENCODER

#include "sensor/EncoderManager.h"
#include "control/SignalBus.h"
#include "core/Debug.h"
#include <cstdio>  // for snprintf

// Single global instance pointer (since you already use a single g_encoder).
// The constructor will register itself here.
static EncoderManager* s_globalEncoderMgr = nullptr;

// Exposed so other files (e.g. main.cpp) can query if needed.
EncoderManager* getGlobalEncoderManager() {
    return s_globalEncoderMgr;
}

EncoderManager::EncoderManager() {
    s_globalEncoderMgr = this;
}

// ---- Internal helpers ----

// On ESP32 you *can* use CHANGE on A only and read B inside the ISR.
// That's what we do here. We also install a B ISR so we could upgrade
// to full 4x decoding later if you want.
void EncoderManager::attach(uint8_t id, uint8_t pinA, uint8_t pinB) {
    if (id >= MAX_ENCODERS) {
        DBG_PRINTF("[EncoderManager] attach: id=%u out of range\n", id);
        return;
    }

    if (!hal_) {
        DBG_PRINTLN("[EncoderManager] attach() failed: HAL not set!");
        return;
    }

    Encoder& e = encoders_[id];

    e.pinA = pinA;
    e.pinB = pinB;
    e.count = 0;
    e.initialized = true;

    hal_->pinMode(pinA, hal::PinMode::InputPullup);
    hal_->pinMode(pinB, hal::PinMode::InputPullup);

    DBG_PRINTF("[EncoderManager] attach id=%u pinA=%u pinB=%u\n",
               id, pinA, pinB);

    // Install interrupts (see static ISRs below).
    // We trigger on CHANGE on A, and optionally on B too.
    switch (id) {
        case 0:
            hal_->attachInterrupt(pinA, []() {
                if (s_globalEncoderMgr) s_globalEncoderMgr->handleA(0);
            }, hal::InterruptMode::Change);
            hal_->attachInterrupt(pinB, []() {
                if (s_globalEncoderMgr) s_globalEncoderMgr->handleB(0);
            }, hal::InterruptMode::Change);
            break;

        case 1:
            hal_->attachInterrupt(pinA, []() {
                if (s_globalEncoderMgr) s_globalEncoderMgr->handleA(1);
            }, hal::InterruptMode::Change);
            hal_->attachInterrupt(pinB, []() {
                if (s_globalEncoderMgr) s_globalEncoderMgr->handleB(1);
            }, hal::InterruptMode::Change);
            break;

        default:
            // If you ever bump MAX_ENCODERS and forget to add here:
            DBG_PRINTF("[EncoderManager] attach: no ISR wiring for id=%u\n", id);
            break;
    }
}

int32_t EncoderManager::getCount(uint8_t id) const {
    if (id >= MAX_ENCODERS || !encoders_[id].initialized) {
        return 0;
    }

    // On ESP32 (32-bit Xtensa), a 32-bit aligned read of a volatile int32_t
    // is atomic at the hardware level - no interrupt disable needed.
    // Disabling all interrupts globally causes WiFi/timer jitter.
    // The count field is volatile, ensuring the compiler doesn't cache it.
    return encoders_[id].count;
}

void EncoderManager::reset(uint8_t id) {
    if (id >= MAX_ENCODERS || !encoders_[id].initialized) {
        return;
    }

    // On ESP32, 32-bit aligned write to volatile int32_t is atomic.
    // No need to disable interrupts globally (which causes WiFi jitter).
    encoders_[id].count = 0;
}

// ---- ISR helpers ----

// Quadrature decoding (4x resolution):
//
// For proper quadrature decoding, the direction depends on WHICH signal
// changed (A or B) and the state of the OTHER signal at that moment.
//
// When A changes:
//   - If A == B after the change -> forward  (+1)
//   - If A != B after the change -> backward (-1)
//
// When B changes:
//   - If A != B after the change -> forward  (+1)  <-- OPPOSITE of A rule
//   - If A == B after the change -> backward (-1)
//
// This gives 4 edges per encoder cycle (4x resolution).

void EncoderManager::handleA(uint8_t id) {
    if (id >= MAX_ENCODERS || !encoders_[id].initialized || !hal_) {
        return;
    }
    Encoder& e = encoders_[id];

    int a = hal_->digitalRead(e.pinA);
    int b = hal_->digitalRead(e.pinB);

    // A changed: direction = (A == B) ? +1 : -1
    int dir = (a == b) ? +1 : -1;
    e.count += dir;
}

void EncoderManager::handleB(uint8_t id) {
    if (id >= MAX_ENCODERS || !encoders_[id].initialized || !hal_) {
        return;
    }
    Encoder& e = encoders_[id];

    int a = hal_->digitalRead(e.pinA);
    int b = hal_->digitalRead(e.pinB);

    // B changed: direction = (A != B) ? +1 : -1  (opposite of A rule!)
    int dir = (a != b) ? +1 : -1;
    e.count += dir;
}

void EncoderManager::detach(uint8_t id) {
    if (id >= MAX_ENCODERS) {
        return;
    }
    Encoder& e = encoders_[id];
    if (e.initialized && hal_) {
        hal_->detachInterrupt(e.pinA);
        hal_->detachInterrupt(e.pinB);
    }
    e.initialized = false;
    e.count = 0;
    DBG_PRINTF("[EncoderManager] detach id=%u\n", id);
}

// -----------------------------------------------------------------------------
// Auto-Signals Support
// -----------------------------------------------------------------------------

void EncoderManager::enableAutoSignals(SignalBus* bus, uint16_t rate_hz) {
    signals_ = bus;
    signalRateHz_ = rate_hz > 0 ? rate_hz : 100;
    lastPublishMs_ = 0;

    if (!bus) {
        return;
    }

    // Define auto-signals for each attached encoder
    for (uint8_t id = 0; id < MAX_ENCODERS; ++id) {
        if (encoders_[id].initialized && !signalsDefined_[id]) {
            // Count signal: ENCODER_BASE + id*2
            uint16_t countId = SignalNamespace::ENCODER_BASE + id * 2 + SignalNamespace::ENCODER_COUNT_OFFSET;
            // Velocity signal: ENCODER_BASE + id*2 + 1
            uint16_t velId = SignalNamespace::ENCODER_BASE + id * 2 + SignalNamespace::ENCODER_VEL_OFFSET;

            char countName[32];
            char velName[32];
            snprintf(countName, sizeof(countName), "encoder.%u.count", id);
            snprintf(velName, sizeof(velName), "encoder.%u.vel", id);

            bus->defineAutoSignal(countId, countName, SignalBus::Kind::MEAS, 0.0f);
            bus->defineAutoSignal(velId, velName, SignalBus::Kind::MEAS, 0.0f);

            signalsDefined_[id] = true;
            lastCount_[id] = encoders_[id].count;
            lastCountMs_[id] = 0;

            DBG_PRINTF("[EncoderManager] Auto-signals enabled for encoder %u\n", id);
        }
    }
}

void EncoderManager::disableAutoSignals() {
    signals_ = nullptr;
    lastPublishMs_ = 0;
    DBG_PRINTLN("[EncoderManager] Auto-signals disabled");
}

void EncoderManager::publishToSignals(uint32_t now_ms) {
    if (!signals_) {
        return;
    }

    // Rate limiting
    const uint32_t period_ms = signalRateHz_ > 0 ? (1000 / signalRateHz_) : 10;
    if (lastPublishMs_ > 0 && (now_ms - lastPublishMs_) < period_ms) {
        return;
    }

    for (uint8_t id = 0; id < MAX_ENCODERS; ++id) {
        if (!encoders_[id].initialized || !signalsDefined_[id]) {
            continue;
        }

        int32_t count = encoders_[id].count;
        uint16_t countSigId = SignalNamespace::ENCODER_BASE + id * 2 + SignalNamespace::ENCODER_COUNT_OFFSET;
        uint16_t velSigId = SignalNamespace::ENCODER_BASE + id * 2 + SignalNamespace::ENCODER_VEL_OFFSET;

        // Publish count
        signals_->setAutoSignal(countSigId, static_cast<float>(count), now_ms);

        // Compute and publish velocity (rad/s)
        float velocity = 0.0f;
        if (lastCountMs_[id] > 0 && now_ms > lastCountMs_[id]) {
            uint32_t dt_ms = now_ms - lastCountMs_[id];
            int32_t delta = count - lastCount_[id];
            float dt_s = dt_ms * 0.001f;
            // velocity in rad/s = (delta ticks / ticks_per_rad) / dt_s
            velocity = (static_cast<float>(delta) / ticksPerRad_[id]) / dt_s;
        }
        signals_->setAutoSignal(velSigId, velocity, now_ms);

        lastCount_[id] = count;
        lastCountMs_[id] = now_ms;
    }

    lastPublishMs_ = now_ms;
}

void EncoderManager::setTicksPerRad(uint8_t id, float ticksPerRad) {
    if (id < MAX_ENCODERS && ticksPerRad > 0.0f) {
        ticksPerRad_[id] = ticksPerRad;
    }
}

#endif // HAS_ENCODER
