#pragma once
#include <cstdint>
#include "core/Event.h"

// Forward declaration
namespace mara {
struct ServiceContext;
}

/**
 * Loop domain specifies which execution context a module runs in.
 * This determines scheduling, timing constraints, and allowed operations.
 *
 * MAIN:    Runs in main loop (Core 0). Can allocate, do I/O, parse JSON.
 *          Examples: TelemetryModule, IdentityModule, command handlers
 *
 * CONTROL: Runs in control task (Core 1). NO allocation, NO blocking.
 *          Must complete within timing budget (see RealTimeContract.h).
 *          Examples: ControlKernel, Observer, MotionController
 *
 * SAFETY:  Runs in safety loop (high priority). NO allocation, bounded.
 *          Safety-critical operations only.
 *          Examples: ModeManager watchdog, E-STOP handling
 *
 * ANY:     Module handles its own scheduling or is domain-agnostic.
 *          Examples: HeartbeatModule (timer-driven)
 */
enum class LoopDomain : uint8_t {
    MAIN = 0,     // Main loop - I/O, telemetry, commands
    CONTROL = 1,  // Control task - real-time, no allocation
    SAFETY = 2,   // Safety loop - highest priority
    ANY = 255     // Domain-agnostic or self-scheduled
};

/**
 * Base interface for all modules.
 *
 * Modules follow a lifecycle:
 * 1. Construction (default or with dependencies)
 * 2. init(ServiceContext&) - receive dependencies (for self-registered modules)
 * 3. setup() - one-time initialization
 * 4. loop(now_ms) - called repeatedly from main loop
 * 5. handleEvent(evt) - optional event handling
 *
 * For self-registration using REGISTER_MODULE macro:
 * - Use default constructor
 * - Override init() to receive dependencies from ServiceContext
 *
 * For manual registration via MCUHost::addModule():
 * - Take dependencies in constructor
 * - init() is still called but may be empty
 */
class IModule {
public:
    virtual ~IModule() = default;

    /**
     * Initialize module with service dependencies.
     * Called after all modules are registered, before setup().
     * Self-registered modules should override this to get dependencies.
     */
    virtual void init(mara::ServiceContext& ctx) { (void)ctx; }

    /**
     * One-time setup after init(). Called before loop() starts.
     */
    virtual void setup() {}

    /**
     * Called repeatedly from main loop.
     * @param now_ms Current time in milliseconds
     */
    virtual void loop(uint32_t now_ms) { (void)now_ms; }

    /**
     * Get module name for debugging.
     */
    virtual const char* name() const = 0;

    /**
     * Handle events from EventBus (optional).
     */
    virtual void handleEvent(const Event& evt) { (void)evt; }

    /**
     * Get module priority (lower = earlier in init/setup/loop order).
     * Default is 100. Critical modules should use < 50.
     */
    virtual int priority() const { return 100; }

    /**
     * Get the loop domain this module should run in.
     * Default is MAIN (main loop). Override for control or safety modules.
     * See LoopDomain enum for constraints.
     */
    virtual LoopDomain domain() const { return LoopDomain::MAIN; }
};
