// src/core/MCUHost.cpp

#include "core/MCUHost.h"
#include "core/ModuleManager.h"
#include "core/ServiceContext.h"
#include "core/Debug.h"
#include "command/MessageRouter.h"
#include "core/LoopScheduler.h"
#include "core/LoopRates.h"
#include <Arduino.h>

MCUHost* MCUHost::s_instance = nullptr;

MCUHost::MCUHost(EventBus& bus, MessageRouter* router)
    : bus_(bus)
    , router_(router)
{
    s_instance = this;
}

void MCUHost::addModule(IModule* module) {
    if (module) {
        modules_.push_back(module);
    }
}

void MCUHost::setup(mara::ServiceContext* ctx) {
    ctx_ = ctx;  // Store for use in loop()

    // 1. Finalize and initialize self-registered modules
    ModuleManager* mm = ctx_ ? ctx_->moduleManager : &ModuleManager::instance();
    mm->finalize();

    if (ctx_) {
        mm->initAll(*ctx_);
    }

    // 2. Setup self-registered modules
    mm->setupAll();

    // 3. Setup manually-added modules (legacy pattern)
    for (auto* m : modules_) {
        if (m) m->setup();
    }

    // 4. Subscribe to EventBus
    bus_.subscribe(&MCUHost::onEventStatic);

    DBG_PRINTF("[HOST] Setup complete: %d self-registered, %d manual modules\n",
               (int)mm->moduleCount(), (int)modules_.size());
}

void MCUHost::loop(uint32_t now_ms) {
    // Router/transport handling
    if (routerLoop_) {
        routerLoop_();
    }

    // Rate-limited loops
    static LoopScheduler safetySched(getLoopRates().safety_period_ms());
    static LoopScheduler ctrlSched(getLoopRates().ctrl_period_ms());
    static LoopScheduler telemSched(getLoopRates().telem_period_ms());

    // Update periods dynamically
    safetySched.setPeriodMs(getLoopRates().safety_period_ms());
    ctrlSched.setPeriodMs(getLoopRates().ctrl_period_ms());
    telemSched.setPeriodMs(getLoopRates().telem_period_ms());

    if (safetySched.tick(now_ms)) {
        runSafety(now_ms);
    }

    if (ctrlSched.tick(now_ms)) {
        // Control loop tick - modules handle their own timing internally
        // but this provides a global rate limit
    }

    // Run self-registered modules (prefer explicit wiring via ctx_)
    if (ctx_ && ctx_->moduleManager) {
        ctx_->moduleManager->loopAll(now_ms);
    } else {
        // Fallback to singleton - should not happen in normal operation
        DBG_PRINTLN("[HOST] Warning: using ModuleManager::instance() fallback");
        ModuleManager::instance().loopAll(now_ms);
    }

    // Run manually-added modules (legacy pattern)
    for (auto* m : modules_) {
        if (m) m->loop(now_ms);
    }
}

void MCUHost::onEventStatic(const Event& evt) {
    if (s_instance) {
        s_instance->onEvent(evt);
    }
}

void MCUHost::onEvent(const Event& evt) {
    if (evt.type == EventType::HEARTBEAT) {
        lastHeartbeatMs_ = evt.timestamp_ms;
    }
}

void MCUHost::runSafety(uint32_t now_ms) {
    (void)now_ms;
    // Safety checks run at safety_hz
}