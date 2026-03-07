#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"

#include <Arduino.h>
#include <ArduinoOTA.h>

namespace {

class SetupOtaModule : public mara::ISetupModule {
public:
    const char* name() const override { return "OTA"; }

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        (void)ctx; // OTA doesn't need services

        ArduinoOTA.setHostname("ESP32-bot");

        ArduinoOTA
            .onStart([]() {
                String type = (ArduinoOTA.getCommand() == U_FLASH) ? "sketch" : "filesystem";
                Serial.println("[OTA] Start updating " + type);
            })
            .onEnd([]() {
                Serial.println("\n[OTA] End");
            })
            .onProgress([](unsigned int progress, unsigned int total) {
                Serial.printf("[OTA] Progress: %u%%\r", (progress * 100U) / total);
            })
            .onError([](ota_error_t error) {
                Serial.printf("[OTA] Error[%u]: ", error);
                if (error == OTA_AUTH_ERROR)         Serial.println("Auth Failed");
                else if (error == OTA_BEGIN_ERROR)   Serial.println("Begin Failed");
                else if (error == OTA_CONNECT_ERROR) Serial.println("Connect Failed");
                else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive Failed");
                else if (error == OTA_END_ERROR)     Serial.println("End Failed");
            });

        ArduinoOTA.begin();
        Serial.println("[OTA] Ready. You can now upload OTA as 'ESP32-bot.local'");

        return mara::Result<void>::ok();
    }
};

SetupOtaModule g_setupOta;

} // anonymous namespace

mara::ISetupModule* getSetupOtaModule() {
    return &g_setupOta;
}
