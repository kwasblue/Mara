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

    // Take an atomic-ish snapshot. On ESP32, reading a 32-bit volatile is
    // already atomic, but this guards against weirdness if you want.
    // Use HAL if available, fallback to direct calls for ISR safety
    if (hal_) {
        hal_->disableInterrupts();
    }
    int32_t c = encoders_[id].count;
    if (hal_) {
        hal_->enableInterrupts();
    }
    return c;
}

void EncoderManager::reset(uint8_t id) {
    if (id >= MAX_ENCODERS || !encoders_[id].initialized) {
        return;
    }

    if (hal_) {
        hal_->disableInterrupts();
    }
    encoders_[id].count = 0;
    if (hal_) {
        hal_->enableInterrupts();
    }
}

// ---- ISR helpers ----

// Quadrature rule used:
//   On a change of A or B, read both pins and decide direction.
//   A == B  -> +1
//   A != B  -> -1
//
// We call the same logic from handleA and handleB, so you get up to 4x decoding.
void EncoderManager::handleA(uint8_t id) {
    if (id >= MAX_ENCODERS || !encoders_[id].initialized || !hal_) {
        return;
    }
    Encoder& e = encoders_[id];

    int a = hal_->digitalRead(e.pinA);
    int b = hal_->digitalRead(e.pinB);

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

    int dir = (a == b) ? +1 : -1;
    e.count += dir;
}

#endif // HAS_ENCODER
