// include/core/ModuleManager.h
// Singleton registry for self-registering modules

#pragma once

#include <vector>
#include "core/IModule.h"

// Forward declaration
namespace mara {
struct ServiceContext;
}

/**
 * ModuleManager - Singleton registry for IModule instances.
 *
 * Enables self-registration of modules via REGISTER_MODULE macro,
 * reducing the number of files to edit when adding a new module.
 *
 * Lifecycle:
 * 1. Static constructors call registerModule() before main()
 * 2. finalize() sorts modules by priority
 * 3. initAll(ctx) passes ServiceContext to each module
 * 4. setupAll() calls setup() on each module
 * 5. loopAll(now_ms) calls loop() on each module
 *
 * Thread Safety:
 * - Registration happens before main() (single-threaded)
 * - loopAll() is called from a single thread (main loop)
 *
 * Usage with MCUHost:
 * - ModuleManager handles self-registered modules
 * - MCUHost::addModule() handles manually-added modules
 * - Both can coexist
 */
class ModuleManager {
public:
    /**
     * Get the singleton instance.
     */
    static ModuleManager& instance();

    /**
     * Register a module. Called by REGISTER_MODULE macro.
     * @param module Pointer to static module instance
     */
    void registerModule(IModule* module);

    /**
     * Finalize registrations. Sorts modules by priority.
     * Call once after all static registrations, before initAll().
     */
    void finalize();

    /**
     * Initialize all registered modules with service dependencies.
     * @param ctx ServiceContext with all services
     */
    void initAll(mara::ServiceContext& ctx);

    /**
     * Call setup() on all registered modules.
     * Call after initAll().
     */
    void setupAll();

    /**
     * Call loop() on all registered modules.
     * @param now_ms Current time in milliseconds
     */
    void loopAll(uint32_t now_ms);

    /**
     * Call loop() only on modules in the specified domain.
     * Use this for domain-specific scheduling (e.g., control task).
     * @param now_ms Current time in milliseconds
     * @param domain The loop domain to run
     */
    void loopDomain(uint32_t now_ms, LoopDomain domain);

    /**
     * Get number of registered modules.
     */
    size_t moduleCount() const { return modules_.size(); }

    /**
     * Check if registry has been finalized.
     */
    bool isFinalized() const { return finalized_; }

    /**
     * Check if modules have been initialized.
     */
    bool isInitialized() const { return initialized_; }

    /**
     * Get all registered modules (for MCUHost integration).
     */
    const std::vector<IModule*>& modules() const { return modules_; }

private:
    ModuleManager() = default;
    ModuleManager(const ModuleManager&) = delete;
    ModuleManager& operator=(const ModuleManager&) = delete;

    std::vector<IModule*> modules_;
    bool finalized_ = false;
    bool initialized_ = false;
};
