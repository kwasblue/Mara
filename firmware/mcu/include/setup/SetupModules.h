#pragma once

#include "setup/ISetupModule.h"
#include <cstddef>

namespace mara {
struct ServiceContext;
}

// =============================================================================
// SETUP MODULE MANIFEST
// =============================================================================
// This is the single source of truth for setup module ordering.
// To add a new setup module:
// 1. Create SetupXxx.cpp with your ISetupModule implementation
// 2. Add getSetupXxxModule() declaration below
// 3. Add it to the manifest in SetupManifest.cpp
// =============================================================================

// Individual setup module accessors
mara::ISetupModule* getSetupBleModule();  // Must run BEFORE WiFi for coexistence
mara::ISetupModule* getSetupWifiModule();
mara::ISetupModule* getSetupOtaModule();
mara::ISetupModule* getSetupSafetyModule();
mara::ISetupModule* getSetupTransportModule();
mara::ISetupModule* getSetupMotorsModule();
mara::ISetupModule* getSetupSensorsModule();
mara::ISetupModule* getSetupTelemetryModule();

/**
 * Get the complete setup module manifest.
 * Returns a null-terminated array of setup modules in execution order.
 * Critical modules are marked and will halt the system on failure.
 *
 * Order:
 * 0. Bluetooth - BT controller init (MUST be before WiFi for coexistence)
 * 1. WiFi - Network connectivity
 * 2. OTA - Over-the-air updates
 * 3. Safety - Mode manager, watchdogs (CRITICAL)
 * 4. Motors - Motor drivers, motion controller
 * 5. Sensors - IMU, encoders, ultrasonic
 * 6. Transport - Router, commands, host (CRITICAL)
 * 7. Telemetry - Telemetry providers
 */
mara::ISetupModule** getSetupManifest();

/**
 * Get the number of modules in the manifest.
 */
size_t getSetupManifestSize();
