// src/core/ModuleManager.cpp
// Implementation of ModuleManager singleton

#include "core/ModuleManager.h"
#include "core/ServiceContext.h"
#include "core/Debug.h"
#include <algorithm>

namespace {
const char* domainToString(LoopDomain d) {
    switch (d) {
        case LoopDomain::MAIN:    return "MAIN";
        case LoopDomain::CONTROL: return "CTRL";
        case LoopDomain::SAFETY:  return "SAFE";
        case LoopDomain::ANY:     return "ANY";
        default:                  return "?";
    }
}
} // namespace

ModuleManager& ModuleManager::instance() {
    static ModuleManager manager;
    return manager;
}

void ModuleManager::registerModule(IModule* module) {
    if (!module) return;

    // Check for duplicate registration
    for (auto* m : modules_) {
        if (m == module) {
            DBG_PRINTF("[MMAN] Module already registered: %s\n", module->name());
            return;
        }
    }

    modules_.push_back(module);
    DBG_PRINTF("[MMAN] Registered module: %s (priority=%d)\n",
               module->name(), module->priority());
}

void ModuleManager::finalize() {
    if (finalized_) {
        DBG_PRINTLN("[MMAN] Already finalized");
        return;
    }

    // Sort modules by priority (lower priority first)
    std::sort(modules_.begin(), modules_.end(),
              [](IModule* a, IModule* b) {
                  return a->priority() < b->priority();
              });

    finalized_ = true;
    DBG_PRINTF("[MMAN] Finalized with %d modules\n", (int)modules_.size());

    // Debug: list all modules with domain
    for (auto* module : modules_) {
        DBG_PRINTF("[MMAN]   %s (pri=%d, domain=%s)\n",
                   module->name(), module->priority(), domainToString(module->domain()));
    }
}

void ModuleManager::initAll(mara::ServiceContext& ctx) {
    if (!finalized_) {
        DBG_PRINTLN("[MMAN] Warning: initAll() called before finalize()");
        finalize();
    }

    DBG_PRINTLN("[MMAN] Initializing all modules...");
    for (auto* module : modules_) {
        DBG_PRINTF("[MMAN] init: %s\n", module->name());
        module->init(ctx);
    }

    initialized_ = true;
    DBG_PRINTLN("[MMAN] All modules initialized");
}

void ModuleManager::setupAll() {
    if (!initialized_) {
        DBG_PRINTLN("[MMAN] Warning: setupAll() called before initAll()");
    }

    DBG_PRINTLN("[MMAN] Setting up all modules...");
    for (auto* module : modules_) {
        DBG_PRINTF("[MMAN] setup: %s\n", module->name());
        module->setup();
    }
    DBG_PRINTLN("[MMAN] All modules setup complete");
}

void ModuleManager::loopAll(uint32_t now_ms) {
    for (auto* module : modules_) {
        module->loop(now_ms);
    }
}

void ModuleManager::loopDomain(uint32_t now_ms, LoopDomain domain) {
    for (auto* module : modules_) {
        LoopDomain modDomain = module->domain();
        // Run if exact match or module is domain-agnostic (ANY)
        if (modDomain == domain || modDomain == LoopDomain::ANY) {
            module->loop(now_ms);
        }
    }
}
