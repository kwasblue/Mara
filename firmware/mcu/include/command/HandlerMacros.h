// include/command/HandlerMacros.h
// Self-registration macro for IStringHandler implementations

#pragma once

#include "command/HandlerRegistry.h"

/**
 * REGISTER_HANDLER - Self-register a handler with HandlerRegistry.
 *
 * Creates a static instance of the handler class and registers it
 * with the HandlerRegistry singleton before main() runs.
 *
 * Usage:
 *   class MyHandler : public IStringHandler {
 *       // ... implementation ...
 *   };
 *   REGISTER_HANDLER(MyHandler);
 *
 * Requirements:
 * - Handler class must have a default constructor
 * - Handler class must inherit from IStringHandler
 * - Place REGISTER_HANDLER at file scope (not inside a function)
 *
 * Memory: Handler instances are static (no heap allocation).
 * The handler lives for the entire program duration.
 */
#define REGISTER_HANDLER(ClassName) \
    static ClassName __handler_instance_##ClassName; \
    static struct __registrar_##ClassName { \
        __registrar_##ClassName() { \
            HandlerRegistry::instance().registerHandler(&__handler_instance_##ClassName); \
        } \
    } __registrar_obj_##ClassName
