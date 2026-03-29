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

#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

namespace mara {

// HAL task scheduler (optional)
static hal::ITaskScheduler* g_halScheduler = nullptr;

// Task state
static TaskHandle_t g_controlTaskHandle = nullptr;
static hal::TaskHandle g_halTaskHandle;
static ServiceContext* g_taskCtx = nullptr;
static ControlTaskConfig g_taskConfig;
static volatile bool g_taskRunning = false;

// Statistics (volatile for cross-task access)
static volatile ControlTaskStats g_stats;

// Jitter tracking
static RtTimingStats g_rtStats;

// The FreeRTOS control task
static void controlTaskFunc(void* param) {
    ServiceContext* ctx = static_cast<ServiceContext*>(param);

    TickType_t lastWake = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(1000 / g_taskConfig.rate_hz);

    g_taskRunning = true;
    g_rtStats.target_period_us = 1000000 / g_taskConfig.rate_hz;

    Serial.printf("[CTRL_TASK] Started on Core %d at %d Hz (period=%d ticks)\n",
                  xPortGetCoreID(), g_taskConfig.rate_hz, (int)period);

    uint32_t last_iteration_us = micros();

    for (;;) {
        uint32_t start_us = micros();
        uint32_t now_ms = millis();

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
            ctx->control->graph().step(now_ms, ctx->mode, ctx->gpio, ctx->servo, ctx->imu);
        }

        RT_ZONE_END();
        // =====================================================================
        // END REAL-TIME CRITICAL ZONE
        // =====================================================================

        // Compute execution time
        uint32_t exec_us = micros() - start_us;
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

        // Wait until next period - vTaskDelayUntil provides precise timing
        vTaskDelayUntil(&lastWake, period);
    }
}

void setControlTaskHal(hal::ITaskScheduler* scheduler) {
    g_halScheduler = scheduler;
}

bool startControlTask(ServiceContext& ctx, const ControlTaskConfig& config) {
    // Check if already running (either HAL or direct)
    if (g_controlTaskHandle != nullptr || (g_halScheduler && g_halTaskHandle.native != nullptr)) {
        Serial.println("[CTRL_TASK] Already running");
        return false;
    }

    // Validate config
    if (config.rate_hz < 10 || config.rate_hz > 1000) {
        Serial.printf("[CTRL_TASK] Invalid rate: %d Hz (must be 10-1000)\n", config.rate_hz);
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

    // Use HAL if available
    if (g_halScheduler) {
        hal::TaskConfig halConfig;
        halConfig.name = "ControlTask";
        halConfig.stackSize = config.stack_size;
        halConfig.priority = config.priority;
        halConfig.core = config.core;

        if (!g_halScheduler->createTask(controlTaskFunc, &ctx, halConfig, g_halTaskHandle)) {
            Serial.println("[CTRL_TASK] Failed to create task via HAL");
            g_halTaskHandle.native = nullptr;
            return false;
        }
        return true;
    }

    // Direct FreeRTOS path (legacy)
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
        Serial.println("[CTRL_TASK] Failed to create task");
        g_controlTaskHandle = nullptr;
        return false;
    }

    return true;
}

void stopControlTask() {
    Serial.println("[CTRL_TASK] Stopping...");

    // Use HAL if available and task was created via HAL
    if (g_halScheduler && g_halTaskHandle.native != nullptr) {
        g_halScheduler->deleteTask(g_halTaskHandle);
        g_halTaskHandle.native = nullptr;
        g_taskRunning = false;
        g_taskCtx = nullptr;
        Serial.println("[CTRL_TASK] Stopped (HAL)");
        return;
    }

    // Direct FreeRTOS path
    if (g_controlTaskHandle == nullptr) {
        return;
    }

    // Delete the task
    vTaskDelete(g_controlTaskHandle);
    g_controlTaskHandle = nullptr;
    g_taskRunning = false;
    g_taskCtx = nullptr;

    Serial.println("[CTRL_TASK] Stopped");
}

bool isControlTaskRunning() {
    if (g_halScheduler && g_halTaskHandle.native != nullptr) {
        return g_taskRunning;
    }
    return g_taskRunning && g_controlTaskHandle != nullptr;
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
