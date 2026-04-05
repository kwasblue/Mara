// src/setup/SetupOta.cpp
// OTA setup module using HAL abstraction

#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"
#include "config/GeneratedBuildConfig.h"
#include "hal/IOta.h"
#include "hal/ILogger.h"
#include "core/Debug.h"

// OTA password configuration
// SECURITY: Override OTA_PASSWORD in WifiSecrets.h or build_flags for production!
// An empty password disables OTA authentication entirely (INSECURE).
#ifndef OTA_PASSWORD
    #define OTA_PASSWORD ""  // Default: no password (development only)
    #if PLATFORM_ESP32
        #warning "OTA_PASSWORD not set - OTA updates are unauthenticated! Set in WifiSecrets.h or build_flags."
    #endif
#endif

// OTA hostname defaults to device name from config
#ifndef OTA_HOSTNAME
    #define OTA_HOSTNAME MARA_DEVICE_NAME
#endif

namespace {

class SetupOtaModule : public mara::ISetupModule {
public:
    const char* name() const override { return "OTA"; }

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        hal::ILogger* logger = ctx.halLogger;

        // Use HAL OTA interface if available
        if (ctx.halOta == nullptr) {
            if (logger) logger->println("[OTA] Warning: HAL OTA not available, skipping setup");
            return mara::Result<void>::ok();
        }

        hal::IOta* ota = ctx.halOta;

        // Configure OTA settings via HAL
        ota->setHostname(OTA_HOSTNAME);

        // Set password if configured (empty string = no auth)
        const char* password = OTA_PASSWORD;
        if (password != nullptr && password[0] != '\0') {
            ota->setPassword(password);
            if (logger) logger->println("[OTA] Password authentication enabled");
        } else {
            if (logger) logger->println("[OTA] WARNING: No OTA password set - updates are unauthenticated!");
        }

        // Register callbacks via HAL (use DBG_* macros since lambdas are static)
        ota->onStart([](hal::OtaType type) {
            const char* typeStr = (type == hal::OtaType::FIRMWARE) ? "firmware" : "filesystem";
            DBG_PRINTF("[OTA] Start updating %s\n", typeStr);
        });

        ota->onEnd([]() {
            DBG_PRINTLN("\n[OTA] End");
        });

        ota->onProgress([](uint32_t progress, uint32_t total) {
            DBG_PRINTF("[OTA] Progress: %u%%\r", (progress * 100U) / total);
        });

        ota->onError([](hal::OtaError error) {
            const char* errorStr = "Unknown";
            switch (error) {
                case hal::OtaError::AUTH_FAILED:    errorStr = "Auth Failed"; break;
                case hal::OtaError::BEGIN_FAILED:   errorStr = "Begin Failed"; break;
                case hal::OtaError::CONNECT_FAILED: errorStr = "Connect Failed"; break;
                case hal::OtaError::RECEIVE_FAILED: errorStr = "Receive Failed"; break;
                case hal::OtaError::END_FAILED:     errorStr = "End Failed"; break;
                default: break;
            }
            DBG_PRINTF("[OTA] Error: %s\n", errorStr);
        });

        // Initialize OTA system (HAL has duplicate-init guard)
        ota->begin();

        if (logger) logger->printf("[OTA] Ready. Hostname: %s.local\n", OTA_HOSTNAME);

        return mara::Result<void>::ok();
    }
};

SetupOtaModule g_setupOta;

} // anonymous namespace

mara::ISetupModule* getSetupOtaModule() {
    return &g_setupOta;
}
