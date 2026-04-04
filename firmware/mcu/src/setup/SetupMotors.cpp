#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"
#include "hal/ILogger.h"
#include "config/PinConfig.h"
#include "config/PlatformConfig.h"

#if PLATFORM_HAS_ARDUINO
#include <Arduino.h>
#endif
#include "config/FeatureFlags.h"
#include "config/GpioChannelDefs.h"
#include "hw/GpioManager.h"
#include "hw/PwmManager.h"
#include "motor/DcMotorManager.h"
#include "motor/StepperManager.h"
#include "motor/ActuatorConfig.h"
#include "motor/IActuator.h"  // For ActuatorCap

// Include all self-registering actuators (triggers static registration)
#include "motor/AllActuators.h"

namespace {

class SetupMotorsModule : public mara::ISetupModule {
public:
    const char* name() const override { return "Motors"; }

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        if (!ctx.gpio) {
            return mara::Result<void>::err(mara::ErrorCode::NotInitialized);
        }

        // Setup status LED via HAL
        if (ctx.halGpio) {
            ctx.halGpio->pinMode(Pins::LED_STATUS, hal::PinMode::Output);
            ctx.halGpio->digitalWrite(Pins::LED_STATUS, 0);
        }

        // Register GPIO channels from auto-generated definitions
        for (size_t i = 0; i < GPIO_CHANNEL_COUNT; ++i) {
            const auto& def = GPIO_CHANNEL_DEFS[i];
            ctx.gpio->registerChannel(def.channel, def.pin, def.mode);
        }

        // Build actuator capability mask from feature flags
        uint32_t actuatorCaps = 0;
#if HAS_DC_MOTOR
        actuatorCaps |= mara::ActuatorCap::DC_MOTOR;
#endif
#if HAS_SERVO
        actuatorCaps |= mara::ActuatorCap::SERVO;
#endif
#if HAS_STEPPER
        actuatorCaps |= mara::ActuatorCap::STEPPER;
#endif
#if HAS_ENCODER
        actuatorCaps |= mara::ActuatorCap::ENCODER;
#endif

        // Initialize self-registered actuators
        if (ctx.actuatorRegistry) {
            ctx.actuatorRegistry->setAvailableCaps(actuatorCaps);
            ctx.actuatorRegistry->initAll(ctx);
            ctx.actuatorRegistry->setupAll();
            if (ctx.halLogger) {
                ctx.halLogger->printf("[MOTORS] Initialized %zu self-registered actuators\n",
                                      ctx.actuatorRegistry->count());
            }
        }

        // Legacy actuators (until fully migrated)
        // Auto-configure steppers from Pins::
        if (ctx.stepper) {
            mara::autoConfigureSteppers(*ctx.stepper);
            ctx.stepper->dumpAllStepperMappings();
        }

        // Legacy DC motors (can be removed once DcMotorActuator is fully tested)
        if (ctx.dcMotor) {
            int dcCount = mara::autoConfigureDcMotors(*ctx.dcMotor);
            if (ctx.halLogger) {
                ctx.halLogger->printf("[MOTORS] Legacy: Auto-configured %d DC motors\n", dcCount);
            }
            ctx.dcMotor->dumpAllMotorMappings();
        }

        // Auto-configure encoders from Pins::
        if (ctx.encoder) {
            mara::autoConfigureEncoders(*ctx.encoder);
        }

        if (ctx.halLogger) ctx.halLogger->println("[MOTORS] GPIO and actuators configured");

        return mara::Result<void>::ok();
    }
};

SetupMotorsModule g_setupMotors;

} // anonymous namespace

mara::ISetupModule* getSetupMotorsModule() {
    return &g_setupMotors;
}
