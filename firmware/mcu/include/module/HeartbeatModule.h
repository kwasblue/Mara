#pragma once
#include "core/IModule.h"
#include "core/EventBus.h"

class HeartbeatModule : public IModule {
public:
    explicit HeartbeatModule(EventBus& bus)
        : bus_(bus) {}

    void setup() override {
        lastBeatMs_ = 0;
    }

    void loop(uint32_t now_ms) override {
        const uint32_t PERIOD_MS = 10000; // 0.1 Hz (every 10 seconds)
        if (now_ms - lastBeatMs_ >= PERIOD_MS) {
            lastBeatMs_ = now_ms;
            Event evt{ EventType::HEARTBEAT, now_ms, EventPayload{} };
            bus_.publish(evt);
        }
    }
    const char* name() const override { return "HeartbeatModule"; }

private:
    EventBus& bus_;
    uint32_t  lastBeatMs_ = 0;
};
