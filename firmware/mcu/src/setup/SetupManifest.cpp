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
// - BLE FIRST: Must init BT controller before WiFi for coexistence
// - WiFi/OTA next: needed for debugging and recovery
// - Safety before motors: ensures state machine is ready
// - Motors before sensors: actuators should be ready first
// - Transport after motors/sensors: can query state
// - Telemetry last: needs all providers registered
//
mara::ISetupModule* g_setupManifest[] = {
    // --- Bluetooth (must be before WiFi!) ---
    nullptr,  // [0] Bluetooth - BT controller init

    // --- Network ---
    nullptr,  // [1] WiFi - populated at runtime (getSetupWifiModule())
    nullptr,  // [2] OTA  - populated at runtime (getSetupOtaModule())

    // --- Safety (CRITICAL) ---
    nullptr,  // [3] Safety - ModeManager, watchdogs

    // --- Actuators ---
    nullptr,  // [4] Motors - DC motors, servos, steppers

    // --- Sensors ---
    nullptr,  // [5] Sensors - IMU, encoders, ultrasonic, lidar

    // --- Communication (CRITICAL) ---
    nullptr,  // [6] Transport - Router, commands, host

    // --- Telemetry ---
    nullptr,  // [7] Telemetry - Providers registration

    // Null terminator
    nullptr
};

constexpr size_t MANIFEST_SIZE = 8;  // Excluding null terminator

bool g_manifestPopulated = false;

void populateManifest() {
    if (g_manifestPopulated) return;

    g_setupManifest[0] = getSetupBleModule();
    g_setupManifest[1] = getSetupWifiModule();
    g_setupManifest[2] = getSetupOtaModule();
    g_setupManifest[3] = getSetupSafetyModule();
    g_setupManifest[4] = getSetupMotorsModule();
    g_setupManifest[5] = getSetupSensorsModule();
    g_setupManifest[6] = getSetupTransportModule();
    g_setupManifest[7] = getSetupTelemetryModule();

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
