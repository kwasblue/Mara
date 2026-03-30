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

#if PLATFORM_HAS_ARDUINO
#include <Arduino.h>
#endif

#if HAS_FREERTOS
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#endif

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
static volatile bool g_taskRunning = false;

// Statistics (volatile for cross-task access)
static volatile ControlTaskStats g_stats;

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

    g_taskRunning = true;
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

#if PLATFORM_HAS_ARDUINO
    Serial.printf("[CTRL_TASK] Started on Core %d at %d Hz (period=%lu ticks)\n",
                  core, g_taskConfig.rate_hz, (unsigned long)periodTicks);
#endif

    // Get clock for timing (use system clock if no HAL clock available)
    auto& sysClock = mara::getSystemClock();
    uint32_t last_iteration_us = sysClock.micros();

    for (;;) {
        uint32_t start_us = sysClock.micros();
        uint32_t now_ms = sysClock.millis();

        // Track period jitter (time since last iteration)
        if (g_stats.iterations > 0) {
            uint32_t period_us = start_us - last_iteration_us;
            g_rtStats.recordPeriod(period_us);
        }
        last_iteration_us = start_us;

        // Compute dt based on configured rate
        float dt_s = 1.0f / g_taskConfig.rate_hz;

        // =====================================================================
        // REAL-TIME CRITICAL ZONE
        // All code in this zone must be RT_SAFE - no heap allocation, no blocking
        // =====================================================================
        RT_ZONE_BEGIN("ControlLoop");

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
                    if (ctx->motion) {
                        if (servo.duration_ms == 0) {
                            if (ctx->servo) {
                                ctx->servo->setAngle(servo.servo_id, servo.angle_deg);
                            }
                        } else {
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
                for (uint8_t i = 0; i < composite.stepper_move_count; ++i) {
                    if (ctx->motion) {
                        const auto& step = composite.stepper_moves[i];
                        ctx->motion->moveStepperRelative(step.motor_id, step.steps, step.speed_steps_s);
                    }
                }
            }

            // Servo intents (per-servo)
            for (uint8_t i = 0; i < mara::IntentBuffer::MAX_SERVO_INTENTS; ++i) {
                mara::ServoIntent servo;
                if (ctx->intents->consumeServoIntent(i, servo)) {
                    if (ctx->motion) {
                        if (servo.duration_ms == 0) {
                            // Immediate move
                            if (ctx->servo) {
                                ctx->servo->setAngle(servo.id, servo.angle_deg);
                            }
                        } else {
                            // Interpolated move
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
            for (int i = 0; i < mara::IntentBuffer::MAX_STEPPER_INTENTS; ++i) {
                mara::StepperIntent step;
                if (ctx->intents->consumeStepperIntent(i, step)) {
                    if (ctx->motion) {
                        ctx->motion->moveStepperRelative(step.motor_id, step.steps, step.speed_steps_s);
                    }
                }
            }

            // Signal intents (consume all queued)
            mara::SignalIntent sig;
            while (ctx->intents->consumeSignalIntent(sig)) {
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
        g_stats.last_exec_us = exec_us;
        g_stats.iterations++;

        if (exec_us > g_stats.max_exec_us) {
            g_stats.max_exec_us = exec_us;
        }

        // Check for overrun (execution took longer than period)
        uint32_t period_us = 1000000 / g_taskConfig.rate_hz;
        if (exec_us > period_us) {
            g_stats.overruns++;
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
#if PLATFORM_HAS_ARDUINO
        Serial.println("[CTRL_TASK] Already running");
#endif
        return false;
    }

    // Validate config
    if (config.rate_hz < 10 || config.rate_hz > 1000) {
#if PLATFORM_HAS_ARDUINO
        Serial.printf("[CTRL_TASK] Invalid rate: %d Hz (must be 10-1000)\n", config.rate_hz);
#endif
        return false;
    }

    g_taskCtx = &ctx;
    g_taskConfig = config;

    // Reset stats (individual fields for volatile)
    g_stats.iterations = 0;
    g_stats.max_exec_us = 0;
    g_stats.overruns = 0;
    g_stats.last_exec_us = 0;
    g_stats.min_period_us = 0;
    g_stats.max_period_us = 0;
    g_stats.jitter_violations = 0;
    g_rtStats.reset();

    // Use HAL scheduler if available (preferred path)
    if (g_halScheduler) {
        hal::TaskConfig halConfig;
        halConfig.name = "ControlTask";
        halConfig.stackSize = config.stack_size;
        halConfig.priority = config.priority;
        halConfig.core = config.core;

        if (!g_halScheduler->createTask(controlTaskFunc, &ctx, halConfig, g_halTaskHandle)) {
#if PLATFORM_HAS_ARDUINO
            Serial.println("[CTRL_TASK] Failed to create task via HAL");
#endif
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
#if PLATFORM_HAS_ARDUINO
        Serial.println("[CTRL_TASK] Failed to create task");
#endif
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
#if PLATFORM_HAS_ARDUINO
    Serial.println("[CTRL_TASK] Stopping...");
#endif

    // Use HAL if available and task was created via HAL
    if (g_halScheduler && g_halTaskHandle.native != nullptr) {
        g_halScheduler->deleteTask(g_halTaskHandle);
        g_halTaskHandle.native = nullptr;
        g_taskRunning = false;
        g_taskCtx = nullptr;
#if PLATFORM_HAS_ARDUINO
        Serial.println("[CTRL_TASK] Stopped (HAL)");
#endif
        return;
    }

#if HAS_FREERTOS
    // Direct FreeRTOS path
    if (g_controlTaskHandle == nullptr) {
        return;
    }

    // Delete the task
    vTaskDelete(g_controlTaskHandle);
    g_controlTaskHandle = nullptr;
    g_taskRunning = false;
    g_taskCtx = nullptr;

#if PLATFORM_HAS_ARDUINO
    Serial.println("[CTRL_TASK] Stopped");
#endif
#endif // HAS_FREERTOS
}

bool isControlTaskRunning() {
    if (g_halScheduler && g_halTaskHandle.native != nullptr) {
        return g_taskRunning;
    }
#if HAS_FREERTOS
    return g_taskRunning && g_controlTaskHandle != nullptr;
#else
    return g_taskRunning;
#endif
}

ControlTaskStats getControlTaskStats() {
    // Return a copy (volatile reads)
    ControlTaskStats stats;
    stats.iterations = g_stats.iterations;
    stats.max_exec_us = g_stats.max_exec_us;
    stats.overruns = g_stats.overruns;
    stats.last_exec_us = g_stats.last_exec_us;
    // Jitter stats
    stats.min_period_us = (g_rtStats.min_period_us == UINT32_MAX) ? 0 : g_rtStats.min_period_us;
    stats.max_period_us = g_rtStats.max_period_us;
    stats.jitter_violations = g_rtStats.jitter_violations;
    return stats;
}

void resetControlTaskStats() {
    g_stats.iterations = 0;
    g_stats.max_exec_us = 0;
    g_stats.overruns = 0;
    g_stats.last_exec_us = 0;
    g_stats.min_period_us = 0;
    g_stats.max_period_us = 0;
    g_stats.jitter_violations = 0;
    g_rtStats.reset();
}

} // namespace mara
