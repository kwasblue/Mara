#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"

#include <Arduino.h>
#include "command/ModeManager.h"
#include "motor/MotionController.h"
#include "motor/DcMotorManager.h"
#include "motor/StepperManager.h"

namespace {

class SetupSafetyModule : public mara::ISetupModule {
public:
    const char* name() const override { return "Safety"; }
    bool isCritical() const override { return true; }  // System cannot run safely without this

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        if (!ctx.mode) {
            return mara::Result<void>::err(mara::ErrorCode::NotInitialized);
        }

        SafetyConfig config;
        config.host_timeout_ms   = 2000;
        config.motion_timeout_ms = 2000;
        config.max_linear_vel    = 0.5f;
        config.max_angular_vel   = 2.0f;

        config.estop_pin  = -1;  // TODO: Wire physical E-stop button
        config.bypass_pin = -1;  // TODO: Wire bypass switch
        config.relay_pin  = -1;  // TODO: Wire motor power relay

        ctx.mode->configure(config);
        ctx.mode->begin();

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
