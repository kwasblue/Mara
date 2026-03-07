// include/core/ModuleMacros.h
// Self-registration macro for IModule implementations

#pragma once

#include "core/ModuleManager.h"

/**
 * REGISTER_MODULE - Self-register a module with ModuleManager.
 *
 * Creates a static instance of the module class and registers it
 * with the ModuleManager singleton before main() runs.
 *
 * Usage:
 *   class MyModule : public IModule {
 *   public:
 *       MyModule() = default;  // Must have default constructor
 *
 *       void init(mara::ServiceContext& ctx) override {
 *           bus_ = ctx.bus;  // Get dependencies from context
 *       }
 *
 *       void setup() override { ... }
 *       void loop(uint32_t now_ms) override { ... }
 *       const char* name() const override { return "MyModule"; }
 *
 *   private:
 *       EventBus* bus_ = nullptr;
 *   };
 *   REGISTER_MODULE(MyModule);
 *
 * Requirements:
 * - Module class must have a default constructor
 * - Module class must inherit from IModule
 * - Place REGISTER_MODULE at file scope (not inside a function)
 * - Override init(ServiceContext&) to receive dependencies
 *
 * Memory: Module instances are static (no heap allocation).
 * The module lives for the entire program duration.
 */
#define REGISTER_MODULE(ClassName) \
    static ClassName __module_instance_##ClassName; \
    static struct __module_registrar_##ClassName { \
        __module_registrar_##ClassName() { \
            ModuleManager::instance().registerModule(&__module_instance_##ClassName); \
        } \
    } __module_registrar_obj_##ClassName
