#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"

#include <Arduino.h>
#include <ArduinoJson.h>
#include "module/TelemetryModule.h"
#include "command/ModeManager.h"
#include "core/LoopRates.h"
#include "core/LoopTiming.h"
#include "setup/SetupControlTask.h"
#include "sensor/UltrasonicManager.h"
#include "sensor/ImuManager.h"
#include "sensor/LidarManager.h"
#include "sensor/EncoderManager.h"
#include "motor/StepperManager.h"
#include "motor/DcMotorManager.h"

namespace {

class SetupTelemetryModule : public mara::ISetupModule {
public:
    const char* name() const override { return "Telemetry"; }

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        if (!ctx.telemetry) {
            return mara::Result<void>::err(mara::ErrorCode::NotInitialized);
        }

        ctx.telemetry->setInterval(0);

        // Safety/Mode state
        if (ctx.mode) {
            ModeManager* mode = ctx.mode;
            ctx.telemetry->registerProvider(
                "mode",
                [mode](ArduinoJson::JsonObject node) {
                    node["state"]     = maraModeToString(mode->mode());
                    node["can_move"]  = mode->canMove();
                    node["estopped"]  = mode->isEstopped();
                    node["connected"] = mode->isConnected();
                    node["bypassed"]  = mode->isBypassed();
                }
            );
        }

        // Loop rates
        ctx.telemetry->registerProvider(
            "rates",
            [](ArduinoJson::JsonObject node) {
                LoopRates& r = getLoopRates();
                node["ctrl_hz"]   = r.ctrl_hz;
                node["safety_hz"] = r.safety_hz;
                node["telem_hz"]  = r.telem_hz;
            }
        );

        // Loop timing instrumentation
        ctx.telemetry->registerProvider(
            "timing",
            [](ArduinoJson::JsonObject node) {
                mara::LoopTiming& t = mara::getLoopTiming();
                // Current values (microseconds)
                node["safety_us"]    = t.safety_us;
                node["control_us"]   = t.control_us;
                node["telemetry_us"] = t.telemetry_us;
                node["host_us"]      = t.host_us;
                node["total_us"]     = t.total_us;
                // Peak values
                node["safety_peak"]    = t.safety_peak_us;
                node["control_peak"]   = t.control_peak_us;
                node["telemetry_peak"] = t.telemetry_peak_us;
                node["host_peak"]      = t.host_peak_us;
                node["total_peak"]     = t.total_peak_us;
                // Statistics
                node["iterations"] = t.iterations;
                node["overruns"]   = t.overruns;

                // FreeRTOS control task stats (if running)
                node["freertos_ctrl"] = mara::isControlTaskRunning();
                if (mara::isControlTaskRunning()) {
                    mara::ControlTaskStats stats = mara::getControlTaskStats();
                    node["ctrl_task_exec_us"]  = stats.last_exec_us;
                    node["ctrl_task_peak_us"]  = stats.max_exec_us;
                    node["ctrl_task_iters"]    = stats.iterations;
                    node["ctrl_task_overruns"] = stats.overruns;
                }
            }
        );

        // Ultrasonic
        if (ctx.ultrasonic) {
            UltrasonicManager* ultrasonic = ctx.ultrasonic;
            ctx.telemetry->registerProvider(
                "ultrasonic",
                [ultrasonic](ArduinoJson::JsonObject node) {
                    if (!ultrasonic->isAttached(0)) {
                        node["sensor_id"] = 0;
                        node["attached"]  = false;
                        return;
                    }
                    float dist_cm = ultrasonic->readDistanceCm(0);
                    node["sensor_id"]   = 0;
                    node["attached"]    = true;
                    node["ok"]          = (dist_cm >= 0.0f);
                    node["distance_cm"] = (dist_cm >= 0.0f) ? dist_cm : -1.0f;
                }
            );
        }

        // IMU
        if (ctx.imu) {
            ImuManager* imu = ctx.imu;
            ctx.telemetry->registerProvider(
                "imu",
                [imu](ArduinoJson::JsonObject node) {
                    node["online"] = imu->isOnline();
                    if (!imu->isOnline()) {
                        node["ok"] = false;
                        return;
                    }
                    ImuManager::Sample s;
                    bool ok = imu->readSample(s);
                    node["ok"] = ok;
                    if (!ok) return;
                    node["ax_g"]   = s.ax_g;
                    node["ay_g"]   = s.ay_g;
                    node["az_g"]   = s.az_g;
                    node["gx_dps"] = s.gx_dps;
                    node["gy_dps"] = s.gy_dps;
                    node["gz_dps"] = s.gz_dps;
                    node["temp_c"] = s.temp_c;
                }
            );
        }

        // LiDAR
        if (ctx.lidar) {
            LidarManager* lidar = ctx.lidar;
            ctx.telemetry->registerProvider(
                "lidar",
                [lidar](ArduinoJson::JsonObject node) {
                    node["online"] = lidar->isOnline();
                    if (!lidar->isOnline()) {
                        node["ok"] = false;
                        return;
                    }
                    LidarManager::Sample s;
                    bool ok = lidar->readSample(s);
                    node["ok"] = ok;
                    if (!ok) return;
                    node["distance_m"] = s.distance_m;
                }
            );
        }

        // Encoder 0
        if (ctx.encoder) {
            EncoderManager* encoder = ctx.encoder;
            ctx.telemetry->registerProvider(
                "encoder0",
                [encoder](ArduinoJson::JsonObject node) {
                    int32_t ticks = encoder->getCount(0);
                    node["ticks"] = ticks;
                }
            );
        }

        // Stepper 0
        if (ctx.stepper) {
            StepperManager* stepper = ctx.stepper;
            ctx.telemetry->registerProvider(
                "stepper0",
                [stepper](ArduinoJson::JsonObject node) {
                    StepperManager::StepperDebugInfo info;
                    if (!stepper->getStepperDebugInfo(0, info)) {
                        node["motor_id"] = 0;
                        node["attached"] = false;
                        return;
                    }
                    node["motor_id"]        = info.motorId;
                    node["attached"]        = info.attached;
                    node["enabled"]         = info.enabled;
                    node["moving"]          = info.moving;
                    node["dir_forward"]     = info.lastDirForward;
                    node["last_cmd_steps"]  = info.lastCmdSteps;
                    node["last_cmd_speed"]  = info.lastCmdSpeed;
                }
            );
        }

        // DC motor 0
        if (ctx.dcMotor) {
            DcMotorManager* dcMotor = ctx.dcMotor;
            ctx.telemetry->registerProvider(
                "dc_motor0",
                [dcMotor](ArduinoJson::JsonObject node) {
                    DcMotorManager::MotorDebugInfo info;
                    if (!dcMotor->getMotorDebugInfo(0, info)) {
                        node["motor_id"] = 0;
                        node["attached"] = false;
                        return;
                    }
                    node["motor_id"]        = info.id;
                    node["attached"]        = info.attached;
                    node["in1_pin"]         = info.in1Pin;
                    node["in2_pin"]         = info.in2Pin;
                    node["pwm_pin"]         = info.pwmPin;
                    node["ledc_channel"]    = info.ledcChannel;
                    node["speed"]           = info.lastSpeed;
                    node["freq_hz"]         = info.freqHz;
                    node["resolution_bits"] = info.resolution;
                }
            );
        }

        ctx.telemetry->setup();

        Serial.println("[TELEMETRY] Providers registered");

        return mara::Result<void>::ok();
    }
};

SetupTelemetryModule g_setupTelemetry;

} // anonymous namespace

mara::ISetupModule* getSetupTelemetryModule() {
    return &g_setupTelemetry;
}
