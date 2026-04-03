#include "core/ServiceContext.h"
#include "sensor/EncoderManager.h"
#include "motor/DcMotorManager.h"
#include "motor/MotionController.h"
#include "command/ModeManager.h"

namespace mara {

// Maximum expected angular velocity for sanity clamping (rad/s)
// ~300 rad/s ≈ 2865 RPM - beyond this, assume encoder noise/misconfiguration
static constexpr float MAX_OMEGA_RAD_S = 300.0f;

void runControlLoop(ServiceContext& ctx, uint32_t now_ms, float dt) {
    (void)now_ms;  // Unused for now

    // Update velocity PID for all motors with encoder configuration
    if (ctx.encoder && ctx.dcMotor && dt > 0.0f) {
        for (uint8_t id = 0; id < DcMotorManager::MAX_MOTORS; ++id) {
            // Skip motors without encoder config or PID disabled
            if (!ctx.dcMotor->hasEncoderConfig(id) || !ctx.dcMotor->isVelocityPidEnabled(id)) {
                continue;
            }

            // Get encoder channel and ticks per rev for this motor
            uint8_t encCh = ctx.dcMotor->getEncoderChannel(id);
            float ticksPerRev = ctx.dcMotor->getTicksPerRev(id);

            // Guard against misconfiguration: ticksPerRev == 0 would cause divide-by-zero
            // hasEncoderConfig already checks ticksPerRev > 0, but be defensive
            if (ticksPerRev <= 0.0f) {
                continue;
            }

            // Read current encoder count
            int32_t ticks = ctx.encoder->getCount(encCh);
            int32_t lastTicks = ctx.dcMotor->getLastEncoderTicks(id);
            int32_t deltaTicks = ticks - lastTicks;
            ctx.dcMotor->setLastEncoderTicks(id, ticks);

            // Convert to angular velocity
            float revs = static_cast<float>(deltaTicks) / ticksPerRev;
            float omega_rad_s = revs * 2.0f * 3.14159265f / dt;

            // Clamp velocity to reject encoder noise spikes and timing jitter
            // Raw tick deltas can produce unrealistic velocities on noisy encoders
            if (omega_rad_s > MAX_OMEGA_RAD_S) omega_rad_s = MAX_OMEGA_RAD_S;
            if (omega_rad_s < -MAX_OMEGA_RAD_S) omega_rad_s = -MAX_OMEGA_RAD_S;

            // Update PID controller
            ctx.dcMotor->updateVelocityPid(id, omega_rad_s, dt);
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
