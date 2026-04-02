#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"
#include "core/Clock.h"

#include <Arduino.h>
#include "command/ModeManager.h"
#include "motor/MotionController.h"
#include "motor/DcMotorManager.h"
#include "motor/StepperManager.h"
#include "config/MaraConfig.h"
#include "persistence/McuPersistence.h"

namespace {

class SetupSafetyModule : public mara::ISetupModule {
public:
    const char* name() const override { return "Safety"; }
    bool isCritical() const override { return true; }  // System cannot run safely without this

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        if (!ctx.mode) {
            return mara::Result<void>::err(mara::ErrorCode::NotInitialized);
        }

        const auto& maraCfg = config::getMaraConfig();

        SafetyConfig config;
        config.host_timeout_ms   = maraCfg.safety.host_timeout_ms;
        config.motion_timeout_ms = maraCfg.safety.motion_timeout_ms;
        config.max_linear_vel    = maraCfg.safety.max_linear_vel;
        config.max_angular_vel   = maraCfg.safety.max_angular_vel;
        config.estop_pin         = maraCfg.safety.estop_pin;
        config.bypass_pin        = maraCfg.safety.bypass_pin;
        config.relay_pin         = maraCfg.safety.relay_pin;

        ctx.mode->configure(config);
        ctx.mode->begin();
        if (ctx.persistence) {
            ctx.persistence->begin(maraCfg, mara::getSystemClock().millis());
            ctx.persistence->updateFromMode(*ctx.mode, mara::getSystemClock().millis());

            // LIFETIME NOTE: This lambda captures raw pointers by value.
            // This is safe because both mode and persistence are owned by ServiceStorage,
            // which has static lifetime (lives for the entire program duration).
            // The callback is never invoked after these objects are destroyed.
            ctx.mode->onPersistentStateChanged([mode = ctx.mode, persist = ctx.persistence]() {
                persist->updateFromMode(*mode, mara::getSystemClock().millis());
            });
        }

        // Set up stop callback (normal deactivation, timeout, etc.)
        ctx.mode->onStop([ctx]() {
            Serial.println("[SAFETY] Stop triggered!");
            if (ctx.motion) {
                ctx.motion->stop();
            }
            if (ctx.dcMotor) {
                ctx.dcMotor->stopAll();
            }
        });

        // Emergency stop callback - directly disables motors at PWM level
        // This is called during E-stop and doesn't rely on motion controller
        ctx.mode->onEmergencyStop([ctx]() {
            Serial.println("[SAFETY] EMERGENCY STOP - Direct motor disable!");

            // Stop DC motors directly (bypasses motion controller)
            if (ctx.dcMotor) {
                ctx.dcMotor->stopAll();
            }

            // Stop steppers (iterate through possible IDs)
            if (ctx.stepper) {
                for (int i = 0; i < 4; ++i) {  // MAX_STEPPERS = 4
                    ctx.stepper->stop(i);
                }
            }

            // Relay is controlled in ModeManager::update() based on canMove()
            // E-stop sets mode to ESTOPPED, so canMove() returns false, cutting relay
        });

        Serial.println("[SAFETY] ModeManager configured and started");

        return mara::Result<void>::ok();
    }
};

SetupSafetyModule g_setupSafety;

} // anonymous namespace

mara::ISetupModule* getSetupSafetyModule() {
    return &g_setupSafety;
}
