// src/setup/SetupManifest.cpp
// Central manifest for all setup modules
//
// =============================================================================
// TO ADD A NEW SETUP MODULE:
// 1. Create src/setup/SetupXxx.cpp with your ISetupModule implementation
// 2. Add getSetupXxxModule() declaration to include/setup/SetupModules.h
// 3. Add it to g_setupManifest[] below in the correct position
// =============================================================================

#include "setup/SetupModules.h"

namespace {

// The definitive ordered list of setup modules.
// Modules are executed in this order during setup().
// Critical modules (isCritical() = true) will halt the system on failure.
//
// Order rationale:
// - WiFi/OTA first: needed for debugging and recovery
// - Safety before motors: ensures state machine is ready
// - Motors before sensors: actuators should be ready first
// - Transport after motors/sensors: can query state
// - Telemetry last: needs all providers registered
//
mara::ISetupModule* g_setupManifest[] = {
    // --- Network ---
    nullptr,  // [0] WiFi - populated at runtime (getSetupWifiModule())
    nullptr,  // [1] OTA  - populated at runtime (getSetupOtaModule())

    // --- Safety (CRITICAL) ---
    nullptr,  // [2] Safety - ModeManager, watchdogs

    // --- Actuators ---
    nullptr,  // [3] Motors - DC motors, servos, steppers

    // --- Sensors ---
    nullptr,  // [4] Sensors - IMU, encoders, ultrasonic, lidar

    // --- Communication (CRITICAL) ---
    nullptr,  // [5] Transport - Router, commands, host

    // --- Telemetry ---
    nullptr,  // [6] Telemetry - Providers registration

    // Null terminator
    nullptr
};

constexpr size_t MANIFEST_SIZE = 7;  // Excluding null terminator

bool g_manifestPopulated = false;

void populateManifest() {
    if (g_manifestPopulated) return;

    g_setupManifest[0] = getSetupWifiModule();
    g_setupManifest[1] = getSetupOtaModule();
    g_setupManifest[2] = getSetupSafetyModule();
    g_setupManifest[3] = getSetupMotorsModule();
    g_setupManifest[4] = getSetupSensorsModule();
    g_setupManifest[5] = getSetupTransportModule();
    g_setupManifest[6] = getSetupTelemetryModule();

    g_manifestPopulated = true;
}

} // anonymous namespace

mara::ISetupModule** getSetupManifest() {
    populateManifest();
    return g_setupManifest;
}

size_t getSetupManifestSize() {
    return MANIFEST_SIZE;
}
