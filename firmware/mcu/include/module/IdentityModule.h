#pragma once

#include "core/IModule.h"
#include "core/EventBus.h"
#include "core/Event.h"
#include "transport/MultiTransport.h"
#include <atomic>

class IdentityModule : public IModule {
public:
    IdentityModule(EventBus& bus,
                   MultiTransport& transports,
                   const char* name)
        : bus_(bus)
        , transports_(transports)
        , name_(name) {}

    void setup() override;
    void loop(uint32_t now_ms) override;
    const char* name() const override { return "IdentityModule"; }

private:
    EventBus&       bus_;
    MultiTransport& transports_;
    const char*     name_;

    // Thread-safe singleton for event callback routing
    // Written by setup() (main thread), read by onEventStatic (potentially from other cores)
    static std::atomic<IdentityModule*> s_instance;
    static void onEventStatic(const Event& evt);

    // Fix warning: explicitly mark override
    void handleEvent(const Event& evt) override;
};
