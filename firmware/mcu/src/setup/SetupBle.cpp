// src/setup/SetupBle.cpp
// Initialize Bluetooth Classic BEFORE WiFi to avoid coexistence issues

#include "config/FeatureFlags.h"

#if HAS_BLE

#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"
#include "transport/BleTransport.h"
#include <Arduino.h>
#include <esp32-hal-bt.h>

namespace {

class SetupBleModule : public mara::ISetupModule {
public:
    const char* name() const override { return "Bluetooth"; }

    // Not critical - system can work without Bluetooth
    bool isCritical() const override { return false; }

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        // Start the Bluetooth controller BEFORE WiFi
        // This is critical for coexistence - BT must be initialized first
        if (!btStarted()) {
            if (!btStart()) {
                Serial.println("[BLE] FAILED to start Bluetooth controller");
                return mara::Result<void>::err(mara::ErrorCode::NotSupported);
            }
        }

        // Initialize the BLE transport now that the controller is ready
        if (ctx.ble) {
            ctx.ble->begin();
        }

        Serial.println("[BLE] Bluetooth Classic SPP initialized");
        return mara::Result<void>::ok();
    }
};

SetupBleModule g_setupBle;

} // anonymous namespace

mara::ISetupModule* getSetupBleModule() {
    return &g_setupBle;
}

#else // !HAS_BLE

#include "setup/ISetupModule.h"

mara::ISetupModule* getSetupBleModule() {
    return nullptr;
}

#endif // HAS_BLE
