#include "setup/SetupControlTask.h"
#include "core/ServiceContext.h"
#include "core/IntentBuffer.h"
#include "core/RealTimeContract.h"
#include "module/ControlModule.h"
#include "command/ModeManager.h"
#include "motor/MotionController.h"
#include "motor/ServoManager.h"
#include "motor/DcMotorManager.h"
#include "motor/StepperManager.h"
#include "hw/PwmManager.h"
#include "loop/LoopFunctions.h"
#include "config/PlatformConfig.h"
#include "config/FeatureFlags.h"
#include "hal/ITaskScheduler.h"
#include "hal/ILogger.h"
#include "core/Clock.h"
#include "core/Debug.h"
#include "sensor/ImuManager.h"
#include "sensor/EncoderManager.h"

#if PLATFORM_HAS_ARDUINO
#include <Arduino.h>
#endif

#if HAS_FREERTOS
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#endif

#include <atomic>

namespace mara {

// HAL task scheduler (preferred path)
static hal::ITaskScheduler* g_halScheduler = nullptr;
static hal::TaskHandle g_halTaskHandle;

// Task state
#if HAS_FREERTOS
static TaskHandle_t g_controlTaskHandle = nullptr;
#endif
static ServiceContext* g_taskCtx = nullptr;
static ControlTaskConfig g_taskConfig;
static std::atomic<bool> g_taskRunning{false};

// Statistics with atomic fields for cross-task access
// Using std::atomic instead of volatile struct to ensure proper
// load/store semantics on Xtensa (volatile struct doesn't guarantee
// individual member atomicity on all compilers).
struct AtomicControlTaskStats {
    std::atomic<uint32_t> iterations{0};
    std::atomic<uint32_t> max_exec_us{0};
    std::atomic<uint32_t> overruns{0};
    std::atomic<uint32_t> last_exec_us{0};
    // These are only written from control task, read via getControlTaskStats()
    std::atomic<uint32_t> min_period_us{0};
    std::atomic<uint32_t> max_period_us{0};
    std::atomic<uint32_t> jitter_violations{0};
};
static AtomicControlTaskStats g_stats;

// Jitter tracking
static RtTimingStats g_rtStats;

// The control task function (runs on dedicated core/thread)
static void controlTaskFunc(void* param) {
    ServiceContext* ctx = static_cast<ServiceContext*>(param);

    // Use HAL scheduler for timing if available
    uint32_t lastWake = 0;
    uint32_t periodTicks = 0;

    if (g_halScheduler) {
        lastWake = g_halScheduler->getTickCount();
        periodTicks = g_halScheduler->msToTicks(1000 / g_taskConfig.rate_hz);
    }
#if HAS_FREERTOS
    else {
        // Legacy FreeRTOS path
        lastWake = xTaskGetTickCount();
        periodTicks = pdMS_TO_TICKS(1000 / g_taskConfig.rate_hz);
    }
#endif

    g_taskRunning.store(true, std::memory_order_release);
    g_rtStats.target_period_us = 1000000 / g_taskConfig.rate_hz;

    // Log startup - use HAL logger if available
    uint8_t core = 0;
    if (g_halScheduler) {
        core = g_halScheduler->getCurrentCore();
    }
#if HAS_FREERTOS
    else {
        core = xPortGetCoreID();
    }
#endif

    DBG_PRINTF("[CTRL_TASK] Started on Core %d at %d Hz (period=%lu ticks)\n",
               core, g_taskConfig.rate_hz, (unsigned long)periodTicks);

    // Get clock for timing (use system clock if no HAL clock available)
    auto& sysClock = mara::getSystemClock();
    uint32_t last_iteration_us = sysClock.micros();

    for (;;) {
        uint32_t start_us = sysClock.micros();
        uint32_t now_ms = sysClock.millis();

        // Track period jitter (time since last iteration) and compute actual dt
        float dt_s;
        if (g_stats.iterations.load(std::memory_order_relaxed) > 0) {
            uint32_t period_us = start_us - last_iteration_us;
            g_rtStats.recordPeriod(period_us);

            // Use measured dt, clamped to sane range to prevent integration blow-up
            // Min: 0.5x nominal period, Max: 2x nominal period
            uint32_t nominal_period_us = 1000000 / g_taskConfig.rate_hz;
            uint32_t min_period_us = nominal_period_us / 2;
            uint32_t max_period_us = nominal_period_us * 2;

            if (period_us < min_period_us) {
                period_us = min_period_us;
            } else if (period_us > max_period_us) {
                period_us = max_period_us;
            }
            dt_s = static_cast<float>(period_us) / 1000000.0f;
        } else {
            // First iteration - use nominal dt
            dt_s = 1.0f / g_taskConfig.rate_hz;
        }
        last_iteration_us = start_us;

        // =====================================================================
        // REAL-TIME CRITICAL ZONE
        // All code in this zone must be RT_SAFE - no heap allocation, no blocking
        // =====================================================================
        RT_ZONE_BEGIN("ControlLoop");

        // =====================================================================
        // Publish auto-signals from hardware managers
        // This runs BEFORE consuming intents so control algorithms get fresh data
        // =====================================================================
        if (ctx->imu && ctx->imu->autoSignalsEnabled()) {
            ctx->imu->publishToSignals(now_ms);
        }
        if (ctx->encoder && ctx->encoder->autoSignalsEnabled()) {
            ctx->encoder->publishToSignals(now_ms);
        }

        // =====================================================================
        // Consume intents at deterministic boundary
        // This ensures command bursts don't jitter actuators - only the latest
        // value is used at each control cycle.
        // =====================================================================
        if (ctx->intents) {
            // Velocity intent (latest wins)
            mara::VelocityIntent vel;
            if (ctx->intents->consumeVelocityIntent(vel)) {
                if (ctx->motion) {
                    ctx->motion->setVelocity(vel.vx, vel.omega);
                }
            }
            // Composite/batch intent (latest batch wins, fixed per-family apply order on one control tick)
            mara::CompositeIntent composite;
            if (ctx->intents->consumeCompositeIntent(composite)) {
                for (uint8_t i = 0; i < composite.gpio_count; ++i) {
                    if (ctx->gpio) {
                        ctx->gpio->write(composite.gpio_writes[i].channel, composite.gpio_writes[i].value ? 1 : 0);
                    }
                }
                for (uint8_t i = 0; i < composite.pwm_count; ++i) {
                    if (ctx->pwm) {
                        const auto& pwm = composite.pwm_sets[i];
                        ctx->pwm->set(pwm.channel, pwm.duty, pwm.freq_hz);
                    }
                }
                for (uint8_t i = 0; i < composite.servo_count; ++i) {
                    const auto& servo = composite.servo_sets[i];
                    if (servo.duration_ms == 0) {
                        // Immediate move - only needs ServoManager
                        if (ctx->servo) {
                            ctx->servo->setAngle(servo.servo_id, servo.angle_deg);
                        }
                    } else {
                        // Interpolated move - needs MotionController
                        if (ctx->motion) {
                            ctx->motion->setServoTarget(servo.servo_id, servo.angle_deg, servo.duration_ms);
                        }
                    }
                }
                for (uint8_t i = 0; i < composite.dc_motor_set_count; ++i) {
                    if (ctx->dcMotor) {
                        const auto& motor = composite.dc_motor_sets[i];
                        ctx->dcMotor->setSpeed(motor.motor_id, motor.speed);
                    }
                }
                for (uint8_t i = 0; i < composite.dc_motor_stop_count; ++i) {
                    if (ctx->dcMotor) {
                        ctx->dcMotor->stop(composite.dc_motor_stops[i].motor_id);
                    }
                }
                for (uint8_t i = 0; i < composite.stepper_stop_count; ++i) {
                    if (ctx->stepper) {
                        ctx->stepper->stop(composite.stepper_stops[i].motor_id);
                    }
                }
                // WARNING: Stepper moves are BLOCKING - see comment at stepper intent section
                for (uint8_t i = 0; i < composite.stepper_move_count; ++i) {
                    if (ctx->stepper) {
                        const auto& step = composite.stepper_moves[i];
                        ctx->stepper->moveRelative(step.motor_id, step.steps, step.speed_steps_s);
                    }
                }
            }

            // Servo intents (per-servo)
            for (uint8_t i = 0; i < mara::IntentBuffer::MAX_SERVO_INTENTS; ++i) {
                mara::ServoIntent servo;
                if (ctx->intents->consumeServoIntent(i, servo)) {
                    DBG_PRINTF("[CTRL] Servo intent: id=%d angle=%.1f dur=%u\n",
                               servo.id, servo.angle_deg, servo.duration_ms);
                    if (servo.duration_ms == 0) {
                        // Immediate move - only needs ServoManager
                        if (ctx->servo) {
                            DBG_PRINTF("[CTRL] Calling servo->setAngle(%d, %.1f)\n",
                                       servo.id, servo.angle_deg);
                            ctx->servo->setAngle(servo.id, servo.angle_deg);
                        } else {
                            DBG_PRINTLN("[CTRL] ERROR: ctx->servo is null!");
                        }
                    } else {
                        // Interpolated move - needs MotionController
                        if (ctx->motion) {
                            ctx->motion->setServoTarget(servo.id, servo.angle_deg, servo.duration_ms);
                        }
                    }
                }
            }

            // DC motor intents (per-motor)
            for (uint8_t i = 0; i < mara::IntentBuffer::MAX_DC_MOTOR_INTENTS; ++i) {
                mara::DcMotorIntent dc;
                if (ctx->intents->consumeDcMotorIntent(i, dc)) {
                    if (ctx->dcMotor) {
                        ctx->dcMotor->setSpeed(dc.id, dc.speed);
                    }
                }
            }

            // Stepper intents (per-motor)
            // WARNING: moveRelative() is BLOCKING - it stalls the control loop
            // for the duration of the stepper move (pulses generated in busy-loop).
            // During this time:
            //   - No encoder PID updates
            //   - No velocity commands processed
            //   - No telemetry updates
            // TODO: Consider async stepper driver with interrupt-based stepping
            for (int i = 0; i < static_cast<int>(mara::IntentBuffer::MAX_STEPPER_INTENTS); ++i) {
                mara::StepperIntent step;
                if (ctx->intents->consumeStepperIntent(i, step)) {
                    // Call StepperManager directly (same as motion->moveStepperRelative)
                    // to make the blocking behavior explicit
                    if (ctx->stepper) {
                        ctx->stepper->moveRelative(step.motor_id, step.steps, step.speed_steps_s);
                    }
                }
            }

            // Signal intents (consume all queued, with safety cap)
            // Cap prevents infinite loop if ring buffer is corrupted
            constexpr size_t MAX_SIGNAL_DRAIN = mara::IntentBuffer::MAX_SIGNAL_INTENTS;
            mara::SignalIntent sig;
            for (size_t i = 0; i < MAX_SIGNAL_DRAIN && ctx->intents->consumeSignalIntent(sig); ++i) {
                if (ctx->control) {
                    ctx->control->signals().set(sig.id, sig.value, sig.timestamp_ms);
                }
            }
        }

        // Run full control loop (encoder PID, motion controller)
        runControlLoop(*ctx, now_ms, dt_s);

        // Run control module (PID/LQR slots, observers)
        if (ctx->control) {
            ctx->control->loop(now_ms);
            ctx->control->graph().step(now_ms, ctx->mode, ctx->gpio, ctx->servo, ctx->imu, ctx->encoder, &ctx->control->signals());
        }

        RT_ZONE_END();
        // =====================================================================
        // END REAL-TIME CRITICAL ZONE
        // =====================================================================

        // Compute execution time
        uint32_t exec_us = sysClock.micros() - start_us;
        g_stats.last_exec_us.store(exec_us, std::memory_order_relaxed);
        g_stats.iterations.fetch_add(1, std::memory_order_relaxed);

        // Update max_exec_us atomically (compare-exchange loop)
        uint32_t current_max = g_stats.max_exec_us.load(std::memory_order_relaxed);
        while (exec_us > current_max) {
            if (g_stats.max_exec_us.compare_exchange_weak(
                    current_max, exec_us, std::memory_order_relaxed)) {
                break;
            }
        }

        // Check for overrun (execution took longer than period)
        uint32_t period_us = 1000000 / g_taskConfig.rate_hz;
        if (exec_us > period_us) {
            g_stats.overruns.fetch_add(1, std::memory_order_relaxed);
        }

        // Wait until next period - use HAL scheduler for precise timing
        if (g_halScheduler) {
            g_halScheduler->delayUntil(lastWake, periodTicks);
        }
#if HAS_FREERTOS
        else {
            TickType_t lastWakeTicks = static_cast<TickType_t>(lastWake);
            vTaskDelayUntil(&lastWakeTicks, static_cast<TickType_t>(periodTicks));
            lastWake = static_cast<uint32_t>(lastWakeTicks);
        }
#endif
    }
}

void setControlTaskHal(hal::ITaskScheduler* scheduler) {
    g_halScheduler = scheduler;
}

bool startControlTask(ServiceContext& ctx, const ControlTaskConfig& config) {
    // Check if already running
    bool alreadyRunning = (g_halScheduler && g_halTaskHandle.native != nullptr);
#if HAS_FREERTOS
    alreadyRunning = alreadyRunning || (g_controlTaskHandle != nullptr);
#endif

    if (alreadyRunning) {
        DBG_PRINTLN("[CTRL_TASK] Already running");
        return false;
    }

    // Validate config
    if (config.rate_hz < 10 || config.rate_hz > 1000) {
        DBG_PRINTF("[CTRL_TASK] Invalid rate: %d Hz (must be 10-1000)\n", config.rate_hz);
        return false;
    }

    g_taskCtx = &ctx;
    g_taskConfig = config;

    // Reset stats (atomic stores)
    g_stats.iterations.store(0, std::memory_order_relaxed);
    g_stats.max_exec_us.store(0, std::memory_order_relaxed);
    g_stats.overruns.store(0, std::memory_order_relaxed);
    g_stats.last_exec_us.store(0, std::memory_order_relaxed);
    g_stats.min_period_us.store(0, std::memory_order_relaxed);
    g_stats.max_period_us.store(0, std::memory_order_relaxed);
    g_stats.jitter_violations.store(0, std::memory_order_relaxed);
    g_rtStats.reset();

    // Use HAL scheduler if available (preferred path)
    if (g_halScheduler) {
        hal::TaskConfig halConfig;
        halConfig.name = "ControlTask";
        halConfig.stackSize = config.stack_size;
        halConfig.priority = config.priority;
        halConfig.core = config.core;

        if (!g_halScheduler->createTask(controlTaskFunc, &ctx, halConfig, g_halTaskHandle)) {
            DBG_PRINTLN("[CTRL_TASK] Failed to create task via HAL");
            g_halTaskHandle.native = nullptr;
            return false;
        }
        return true;
    }

#if HAS_FREERTOS
    // Direct FreeRTOS path (legacy fallback)
    BaseType_t result = xTaskCreatePinnedToCore(
        controlTaskFunc,
        "ControlTask",
        config.stack_size,
        &ctx,
        config.priority,
        &g_controlTaskHandle,
        config.core
    );

    if (result != pdPASS) {
        DBG_PRINTLN("[CTRL_TASK] Failed to create task");
        g_controlTaskHandle = nullptr;
        return false;
    }

    return true;
#else
    // No scheduler available - cannot create task
    return false;
#endif
}

void stopControlTask() {
    DBG_PRINTLN("[CTRL_TASK] Stopping...");

    // Signal stop FIRST so task knows to exit cleanly
    g_taskRunning.store(false, std::memory_order_release);

    // Use HAL if available and task was created via HAL
    if (g_halScheduler && g_halTaskHandle.native != nullptr) {
        // Brief delay to let in-progress iteration complete and idle task clean up
        // The control task runs at 100-1000Hz, so 20ms ensures 2-20 iterations pass
        g_halScheduler->delayMs(20);
        g_halScheduler->deleteTask(g_halTaskHandle);
        g_halTaskHandle.native = nullptr;
        g_taskCtx = nullptr;
        DBG_PRINTLN("[CTRL_TASK] Stopped (HAL)");
        return;
    }

#if HAS_FREERTOS
    // Direct FreeRTOS path
    if (g_controlTaskHandle == nullptr) {
        g_taskCtx = nullptr;
        return;
    }

    // Brief delay to let in-progress iteration complete
    vTaskDelay(pdMS_TO_TICKS(20));

    // Delete the task
    vTaskDelete(g_controlTaskHandle);
    g_controlTaskHandle = nullptr;
    g_taskCtx = nullptr;

    DBG_PRINTLN("[CTRL_TASK] Stopped");
#endif // HAS_FREERTOS
}

bool isControlTaskRunning() {
    bool running = g_taskRunning.load(std::memory_order_acquire);
    if (g_halScheduler && g_halTaskHandle.native != nullptr) {
        return running;
    }
#if HAS_FREERTOS
    return running && g_controlTaskHandle != nullptr;
#else
    return running;
#endif
}

ControlTaskStats getControlTaskStats() {
    // Return a copy with atomic loads
    ControlTaskStats stats;
    stats.iterations = g_stats.iterations.load(std::memory_order_relaxed);
    stats.max_exec_us = g_stats.max_exec_us.load(std::memory_order_relaxed);
    stats.overruns = g_stats.overruns.load(std::memory_order_relaxed);
    stats.last_exec_us = g_stats.last_exec_us.load(std::memory_order_relaxed);
    // Jitter stats
    stats.min_period_us = (g_rtStats.min_period_us == UINT32_MAX) ? 0 : g_rtStats.min_period_us;
    stats.max_period_us = g_rtStats.max_period_us;
    stats.jitter_violations = g_rtStats.jitter_violations;
    return stats;
}

void resetControlTaskStats() {
    g_stats.iterations.store(0, std::memory_order_relaxed);
    g_stats.max_exec_us.store(0, std::memory_order_relaxed);
    g_stats.overruns.store(0, std::memory_order_relaxed);
    g_stats.last_exec_us.store(0, std::memory_order_relaxed);
    g_stats.min_period_us.store(0, std::memory_order_relaxed);
    g_stats.max_period_us.store(0, std::memory_order_relaxed);
    g_stats.jitter_violations.store(0, std::memory_order_relaxed);
    g_rtStats.reset();
}

} // namespace mara
