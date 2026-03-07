#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"

#include <Arduino.h>
#include "config/PinConfig.h"
#include "config/FeatureFlags.h"
#include "sensor/ImuManager.h"
#include "sensor/LidarManager.h"
#include "sensor/ISensor.h"

// Include all self-registering sensors (triggers static registration)
#include "sensor/AllSensors.h"

namespace {

/// Build sensor capability mask from feature flags
uint32_t buildSensorCaps() {
    uint32_t caps = 0;
#if HAS_ENCODER
    caps |= mara::SensorCap::ENCODER;
#endif
#if HAS_IMU
    caps |= mara::SensorCap::IMU;
#endif
#if HAS_ULTRASONIC
    caps |= mara::SensorCap::ULTRASONIC;
#endif
#if HAS_LIDAR
    caps |= mara::SensorCap::LIDAR;
#endif
    return caps;
}

class SetupSensorsModule : public mara::ISetupModule {
public:
    const char* name() const override { return "Sensors"; }

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        if (!ctx.sensorRegistry) {
            return mara::Result<void>::err(mara::ErrorCode::NotInitialized);
        }

        // Set available sensor capabilities
        ctx.sensorRegistry->setAvailableCaps(buildSensorCaps());

        // Initialize all self-registered sensors
        ctx.sensorRegistry->initAll();
        Serial.printf("[SENSORS] Initialized %zu self-registered sensors\n",
                      ctx.sensorRegistry->count());

        // Legacy sensors (still using old pattern)
        // TODO: Migrate these to self-registration

        // Initialize IMU
        if (ctx.imu) {
            bool imuOk = ctx.imu->begin(Pins::I2C_SDA, Pins::I2C_SCL, 0x68);
            Serial.printf("[SENSORS] IMU init: %s\n", imuOk ? "OK" : "FAILED");
        }

        // Initialize LiDAR
        if (ctx.lidar) {
            bool lidarOk = ctx.lidar->begin(Pins::I2C_SDA, Pins::I2C_SCL);
            Serial.printf("[SENSORS] LiDAR init: %s\n", lidarOk ? "OK" : "FAILED");
        }

        Serial.println("[SENSORS] Sensor initialization complete");

        return mara::Result<void>::ok();
    }
};

SetupSensorsModule g_setupSensors;

} // anonymous namespace

mara::ISetupModule* getSetupSensorsModule() {
    return &g_setupSensors;
}
