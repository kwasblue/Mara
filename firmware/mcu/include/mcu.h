// include/mcu.h
// Public API for MARA (Modular Asynchronous Robotics Architecture) MCU Firmware
//
// This is the main entry point header for external code integrating with
// the MARA firmware. It exposes the key interfaces and types needed for:
// - Creating custom modules
// - Adding command handlers
// - Extending functionality
//
// For internal implementation details, include specific headers directly.

#pragma once

// =============================================================================
// CORE INTERFACES
// =============================================================================
// These are the stable interfaces external code should depend on

#include "core/IModule.h"           // Module lifecycle interface
#include "core/ITransport.h"        // Transport abstraction
#include "core/ServiceContext.h"    // Dependency injection container
#include "core/Result.h"            // Error handling type

// =============================================================================
// COMMAND SYSTEM
// =============================================================================
// For creating custom command handlers

#include "command/ICommandHandler.h"    // Legacy enum-based handler
#include "command/IStringHandler.h"     // Modern string-based handler
#include "command/CommandContext.h"     // Handler context
#include "command/HandlerMacros.h"      // REGISTER_HANDLER macro

// =============================================================================
// MODULE SYSTEM
// =============================================================================
// For creating self-registering modules

#include "core/ModuleMacros.h"      // REGISTER_MODULE macro
#include "core/ModuleManager.h"     // Module registry

// =============================================================================
// CONFIGURATION
// =============================================================================
// Configuration structs and feature flags

#include "config/FeatureFlags.h"    // HAS_* feature flags
#include "config/MaraConfig.h"     // Unified configuration

// =============================================================================
// RUNTIME
// =============================================================================
// Main runtime entry point

#include "core/Runtime.h"           // Top-level orchestrator
#include "core/MCUHost.h"           // Module host

// =============================================================================
// HEADER ORGANIZATION
// =============================================================================
//
// PUBLIC API HEADERS (stable, external code should use):
// - include/core/IModule.h
// - include/core/ITransport.h
// - include/core/ServiceContext.h
// - include/core/Result.h
// - include/command/ICommandHandler.h
// - include/command/IStringHandler.h
// - include/command/CommandContext.h
// - include/config/FeatureFlags.h
// - include/config/MaraConfig.h
// - include/core/Runtime.h
//
// INTERNAL HEADERS (implementation details, may change):
// - include/core/ServiceStorage.h - Service ownership, not for external use
// - include/command/handlers/*    - Specific handler implementations
// - include/command/decoders/*    - JSON parsing details
// - include/motor/*               - Motor driver internals
// - include/sensor/*              - Sensor driver internals
// - include/transport/*           - Transport implementations
// - include/hw/*                  - Hardware abstraction internals
// - include/loop/*                - Loop function details
// - include/setup/*               - Setup module internals
//
// EXTENSION HEADERS (for extending functionality):
// - include/command/HandlerRegistry.h - For direct registry access
// - include/core/ModuleManager.h      - For direct module management
// - include/control/SignalBus.h       - For control system integration
// - include/control/ControlKernel.h   - For custom controllers
// - include/control/Observer.h        - For state observers
//
// =============================================================================
