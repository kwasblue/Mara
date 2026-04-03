// src/managers/EncoderManager.cpp
#include "config/FeatureFlags.h"

#if HAS_ENCODER

#include "sensor/EncoderManager.h"
#include "core/Debug.h"

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

#endif // HAS_ENCODER
