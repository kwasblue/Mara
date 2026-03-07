#include "core/ServiceContext.h"
#include "sensor/EncoderManager.h"
#include "motor/DcMotorManager.h"
#include "motor/MotionController.h"
#include "command/ModeManager.h"

namespace mara {

// Encoder / PID config for DC motor 0
constexpr float ENCODER0_TICKS_PER_REV = 1632.67f;

// Static state for velocity calculation
static int32_t s_lastTicks = 0;

void runControlLoop(ServiceContext& ctx, uint32_t now_ms, float dt) {
    // DC motor 0 velocity PID (encoder -> omega -> PID -> PWM)
    if (ctx.encoder && ctx.dcMotor) {
        int32_t ticks = ctx.encoder->getCount(0);
        int32_t deltaTicks = ticks - s_lastTicks;
        s_lastTicks = ticks;

        if (dt > 0.0f) {
            float revs = deltaTicks / ENCODER0_TICKS_PER_REV;
            float omega_rad_s = revs * 2.0f * 3.14159265f / dt;
            ctx.dcMotor->updateVelocityPid(0, omega_rad_s, dt);
        }
    }

    // Motion controller update (only if allowed)
    if (ctx.mode && ctx.motion) {
        if (ctx.mode->canMove()) {
            ctx.motion->update(dt);
        }
    }
}

} // namespace mara
