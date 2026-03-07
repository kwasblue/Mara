#pragma once
#include <vector>
#include <functional>

#include "core/EventBus.h"
#include "core/Event.h"
#include "core/IModule.h"

class MessageRouter;  // forward-declare

namespace mara {
struct ServiceContext;
}

/**
 * MCUHost - Central orchestrator for modules and communication.
 *
 * Manages two sources of modules:
 * 1. Manually added via addModule() - legacy pattern
 * 2. Self-registered via REGISTER_MODULE macro - new extensible pattern
 *
 * The setup() and loop() methods handle both seamlessly.
 */
class MCUHost {
public:
    MCUHost(EventBus& bus, MessageRouter* router = nullptr);

    /**
     * Add a module manually (legacy pattern).
     * Use REGISTER_MODULE macro for new modules instead.
     */
    void addModule(IModule* module);

    /**
     * Initialize and finalize all modules.
     * @param ctx ServiceContext for self-registered modules (optional)
     */
    void setup(mara::ServiceContext* ctx = nullptr);

    /**
     * Run all module loops.
     */
    void loop(uint32_t now_ms);

    EventBus& bus() { return bus_; }

    void setRouterLoop(std::function<void()> fn) {
        routerLoop_ = std::move(fn);
    }

private:
    EventBus&             bus_;
    MessageRouter*        router_ = nullptr;
    mara::ServiceContext*  ctx_ = nullptr;  // Stored for explicit registry access
    std::vector<IModule*> modules_;  // Manually added modules
    uint32_t              lastHeartbeatMs_ = 0;
    std::function<void()> routerLoop_;

    void runSafety(uint32_t now_ms);

    // === Static trampoline for EventBus ===
    static MCUHost* s_instance;
    static void onEventStatic(const Event& evt);
    void onEvent(const Event& evt);
};
