#pragma once

#include <Arduino.h>
#include <vector>

#include "core/EventBus.h"

struct LimitSwitchConfig {
    uint8_t  id;
    uint8_t  pin;
    bool     activeHigh;     // true if HIGH = triggered
    uint32_t debounceMs;
};

class LimitSwitchManager {
public:
    explicit LimitSwitchManager(EventBus& bus) : bus_(bus) {}

    void addSwitch(const LimitSwitchConfig& cfg) {
        // Configure pin with correct pull
        pinMode(cfg.pin, cfg.activeHigh ? INPUT_PULLDOWN : INPUT_PULLUP);

        // Read initial state so we don't false-trigger on first poll
        const int raw = digitalRead(cfg.pin);
        const bool active = cfg.activeHigh ? (raw == HIGH) : (raw == LOW);

        switches_.push_back({
            cfg,
            active,           // lastState initialized to current state
            millis()          // lastChangeMs initialized to now
        });
    }

    void poll() {
        const uint32_t now = millis();

        for (auto& s : switches_) {
            const int raw = digitalRead(s.cfg.pin);
            const bool active = s.cfg.activeHigh ? (raw == HIGH) : (raw == LOW);

            // Simple stable-state debounce:
            // Only accept a change if enough time has passed since last accepted change.
            if (active != s.lastState && (now - s.lastChangeMs) >= s.cfg.debounceMs) {
                s.lastState = active;
                s.lastChangeMs = now;

                if (active) {
                    publishTriggered(s.cfg.id);
                } else {
                    publishCleared(s.cfg.id);
                }
            }
        }
    }

private:
    struct SwitchState {
        LimitSwitchConfig cfg;
        bool              lastState;
        uint32_t          lastChangeMs;
    };

    EventBus& bus_;
    std::vector<SwitchState> switches_;

    void publishTriggered(uint8_t id);
    void publishCleared(uint8_t id);
};
