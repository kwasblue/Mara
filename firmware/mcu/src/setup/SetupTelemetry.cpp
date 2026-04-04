#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"
#include "core/Clock.h"

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
#include "telemetry/TelemetrySections.h"
#include "persistence/McuPersistence.h"
#include "module/ControlModule.h"
#include "control/ControlGraphRuntime.h"
#include <algorithm>

namespace {

enum SensorHealthFlags : uint8_t {
    SENSOR_PRESENT  = 1 << 0,
    SENSOR_HEALTHY  = 1 << 1,
    SENSOR_DEGRADED = 1 << 2,
    SENSOR_STALE    = 1 << 3,
};

enum SensorKindCode : uint8_t {
    SENSOR_KIND_IMU = 1,
    SENSOR_KIND_ULTRASONIC = 2,
    SENSOR_KIND_LIDAR = 3,
    SENSOR_KIND_ENCODER = 4,
};

struct SensorHealthEntry {
    uint8_t kind = 0;
    uint8_t sensor_id = 0;
    uint8_t flags = 0;
    uint8_t detail = 0;
};

static SensorHealthEntry buildImuHealth(ImuManager* imu) {
    SensorHealthEntry entry{};
    entry.kind = SENSOR_KIND_IMU;
    if (!imu) return entry;
    entry.flags |= SENSOR_PRESENT;
    if (!imu->isOnline()) {
        entry.flags |= SENSOR_DEGRADED;
        entry.detail = 1;
        return entry;
    }
    ImuManager::Sample sample;
    if (imu->readSample(sample)) {
        entry.flags |= SENSOR_HEALTHY;
    } else {
        entry.flags |= SENSOR_DEGRADED;
        entry.detail = 2;
    }
    return entry;
}

static SensorHealthEntry buildUltrasonicHealth(UltrasonicManager* ultrasonic, uint8_t sensor_id = 0) {
    SensorHealthEntry entry{};
    entry.kind = SENSOR_KIND_ULTRASONIC;
    entry.sensor_id = sensor_id;
    if (!ultrasonic || !ultrasonic->isAttached(sensor_id)) {
        entry.detail = 1;
        return entry;
    }
    entry.flags |= SENSOR_PRESENT;
    const float dist_cm = ultrasonic->readDistanceCm(sensor_id);
    if (dist_cm >= 0.0f) {
        entry.flags |= SENSOR_HEALTHY;
    } else {
        entry.flags |= SENSOR_DEGRADED;
        entry.detail = 2;
    }
    return entry;
}

static SensorHealthEntry buildLidarHealth(LidarManager* lidar) {
    SensorHealthEntry entry{};
    entry.kind = SENSOR_KIND_LIDAR;
    if (!lidar) return entry;
    if (!lidar->isOnline()) {
        entry.detail = 1;
        return entry;
    }
    entry.flags |= SENSOR_PRESENT;
    LidarManager::Sample sample;
    if (lidar->readSample(sample)) {
        entry.flags |= SENSOR_HEALTHY;
    } else {
        entry.flags |= SENSOR_DEGRADED;
        entry.detail = 2;
    }
    return entry;
}

class SetupTelemetryModule : public mara::ISetupModule {
public:
    const char* name() const override { return "Telemetry"; }

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        if (!ctx.telemetry) {
            return mara::Result<void>::err(mara::ErrorCode::NotInitialized);
        }

        ctx.telemetry->setInterval(0);
        // Validate the intended path: emit binary telemetry sections and keep
        // JSON telemetry off unless explicitly needed for debugging.
        ctx.telemetry->setBinaryEnabled(true);
        ctx.telemetry->setJsonEnabled(false);

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
                node["avg_total_us"] = t.avg_total_us;
                node["avg_control_us"] = t.avg_control_us;
                node["avg_telemetry_us"] = t.avg_telemetry_us;
                node["avg_host_us"] = t.avg_host_us;
                node["runtime_ms"] = static_cast<uint32_t>(t.total_runtime_us / 1000ULL);

                // FreeRTOS control task stats (if running)
                node["freertos_ctrl"] = mara::isControlTaskRunning();
                if (mara::isControlTaskRunning()) {
                    mara::ControlTaskStats stats = mara::getControlTaskStats();
                    node["ctrl_task_exec_us"]  = stats.last_exec_us;
                    node["ctrl_task_peak_us"]  = stats.max_exec_us;
                    node["ctrl_task_iters"]    = stats.iterations;
                    node["ctrl_task_overruns"] = stats.overruns;
                    // Jitter stats
                    node["ctrl_task_min_period_us"] = stats.min_period_us;
                    node["ctrl_task_max_period_us"] = stats.max_period_us;
                    node["ctrl_task_jitter_violations"] = stats.jitter_violations;
                }
            }
        );

        if (ctx.mode) {
            ModeManager* mode = ctx.mode;
            TelemetryModule* telemetry = ctx.telemetry;
            ctx.telemetry->registerProvider(
                "perf",
                [mode, telemetry](ArduinoJson::JsonObject node) {
                    const auto& wd = mode->watchdogStats();
                    const auto& pkt = telemetry->packetStats();
                    const auto& t = mara::getLoopTiming();
                    node["hb_count"] = wd.host_heartbeat_count;
                    node["hb_timeouts"] = wd.host_timeout_count;
                    node["hb_recoveries"] = wd.host_recovery_count;
                    node["hb_max_gap_ms"] = wd.max_host_gap_ms;
                    node["motion_cmds"] = wd.motion_command_count;
                    node["motion_timeouts"] = wd.motion_timeout_count;
                    node["motion_max_gap_ms"] = wd.max_motion_gap_ms;
                    node["last_fault"] = wd.last_fault;
                    node["pkt_sent"] = pkt.sent_packets;
                    node["pkt_bytes"] = pkt.sent_bytes;
                    node["pkt_last_bytes"] = pkt.last_packet_bytes;
                    node["pkt_max_bytes"] = pkt.max_packet_bytes;
                    node["pkt_dropped_sections"] = pkt.dropped_sections;
                    node["pkt_buffered"] = pkt.buffered_packets;
                    node["loop_avg_total_us"] = t.avg_total_us;
                    node["loop_total_peak_us"] = t.total_peak_us;
                }
            );

            ctx.telemetry->registerBinProvider(
                TelemetrySections::id(TelemetrySections::SectionId::TELEM_PERF),
                [mode, telemetry](std::vector<uint8_t>& out) {
                    const auto& wd = mode->watchdogStats();
                    const auto& pkt = telemetry->packetStats();
                    const auto& t = mara::getLoopTiming();
                    auto put_u16 = [&out](uint16_t v) {
                        out.push_back(static_cast<uint8_t>(v & 0xFF));
                        out.push_back(static_cast<uint8_t>((v >> 8) & 0xFF));
                    };
                    auto put_u32 = [&out](uint32_t v) {
                        out.push_back(static_cast<uint8_t>(v & 0xFF));
                        out.push_back(static_cast<uint8_t>((v >> 8) & 0xFF));
                        out.push_back(static_cast<uint8_t>((v >> 16) & 0xFF));
                        out.push_back(static_cast<uint8_t>((v >> 24) & 0xFF));
                    };
                    out.push_back(wd.last_fault);
                    put_u32(wd.host_heartbeat_count);
                    put_u32(wd.host_timeout_count);
                    put_u32(wd.host_recovery_count);
                    put_u32(wd.max_host_gap_ms);
                    put_u32(wd.motion_command_count);
                    put_u32(wd.motion_timeout_count);
                    put_u32(wd.max_motion_gap_ms);
                    put_u32(t.iterations);
                    put_u32(t.overruns);
                    put_u16(static_cast<uint16_t>(std::min<uint32_t>(t.avg_total_us, 0xFFFF)));
                    put_u16(static_cast<uint16_t>(std::min<uint32_t>(t.total_peak_us, 0xFFFF)));
                    put_u16(pkt.last_packet_bytes);
                    put_u16(pkt.max_packet_bytes);
                    put_u32(pkt.sent_packets);
                    put_u32(pkt.sent_bytes);
                    put_u32(pkt.dropped_sections);
                    out.push_back(pkt.last_section_count);
                    out.push_back(pkt.max_section_count);
                    out.push_back(static_cast<uint8_t>(std::min<uint16_t>(pkt.buffered_packets, 255)));
                }
            );
        }

        if (ctx.persistence && ctx.mode) {
            // Capture pointers by value - ctx is a local variable that goes out of scope
            // after setup() returns, so capturing by reference would be use-after-return UB
            persistence::McuPersistence* persistence = ctx.persistence;
            ModeManager* mode = ctx.mode;
            ctx.telemetry->registerProvider(
                "persistence",
                [persistence, mode](ArduinoJson::JsonObject node) {
                    persistence->updateFromMode(*mode, mara::getSystemClock().millis());
                    persistence->fillTelemetry(node);
                }
            );
        }

        // Capture sensor pointers by value - ctx goes out of scope after setup()
        ImuManager* sensorImu = ctx.imu;
        UltrasonicManager* sensorUltrasonic = ctx.ultrasonic;
        LidarManager* sensorLidar = ctx.lidar;
        ctx.telemetry->registerProvider(
            "sensor_health",
            [sensorImu, sensorUltrasonic, sensorLidar](ArduinoJson::JsonObject node) {
                ArduinoJson::JsonArray sensors = node["sensors"].to<ArduinoJson::JsonArray>();
                if (sensorImu) {
                    const SensorHealthEntry imu = buildImuHealth(sensorImu);
                    ArduinoJson::JsonObject item = sensors.add<ArduinoJson::JsonObject>();
                    item["kind"] = "imu";
                    item["sensor_id"] = imu.sensor_id;
                    item["present"] = (imu.flags & SENSOR_PRESENT) != 0;
                    item["healthy"] = (imu.flags & SENSOR_HEALTHY) != 0;
                    item["degraded"] = (imu.flags & SENSOR_DEGRADED) != 0;
                    item["stale"] = (imu.flags & SENSOR_STALE) != 0;
                    item["detail"] = imu.detail;
                    item["flags"] = imu.flags;
                }
                if (sensorUltrasonic) {
                    const SensorHealthEntry ultrasonic = buildUltrasonicHealth(sensorUltrasonic, 0);
                    ArduinoJson::JsonObject item = sensors.add<ArduinoJson::JsonObject>();
                    item["kind"] = "ultrasonic";
                    item["sensor_id"] = ultrasonic.sensor_id;
                    item["present"] = (ultrasonic.flags & SENSOR_PRESENT) != 0;
                    item["healthy"] = (ultrasonic.flags & SENSOR_HEALTHY) != 0;
                    item["degraded"] = (ultrasonic.flags & SENSOR_DEGRADED) != 0;
                    item["stale"] = (ultrasonic.flags & SENSOR_STALE) != 0;
                    item["detail"] = ultrasonic.detail;
                    item["flags"] = ultrasonic.flags;
                }
                if (sensorLidar) {
                    const SensorHealthEntry lidar = buildLidarHealth(sensorLidar);
                    ArduinoJson::JsonObject item = sensors.add<ArduinoJson::JsonObject>();
                    item["kind"] = "lidar";
                    item["sensor_id"] = lidar.sensor_id;
                    item["present"] = (lidar.flags & SENSOR_PRESENT) != 0;
                    item["healthy"] = (lidar.flags & SENSOR_HEALTHY) != 0;
                    item["degraded"] = (lidar.flags & SENSOR_DEGRADED) != 0;
                    item["stale"] = (lidar.flags & SENSOR_STALE) != 0;
                    item["detail"] = lidar.detail;
                    item["flags"] = lidar.flags;
                }
            }
        );

        // Reuse the captured pointers from above (sensorImu, sensorUltrasonic, sensorLidar)
        ctx.telemetry->registerBinProvider(
            TelemetrySections::id(TelemetrySections::SectionId::TELEM_SENSOR_HEALTH),
            [sensorImu, sensorUltrasonic, sensorLidar](std::vector<uint8_t>& out) {
                std::vector<SensorHealthEntry> entries;
                entries.reserve(3);
                if (sensorImu) entries.push_back(buildImuHealth(sensorImu));
                if (sensorUltrasonic) entries.push_back(buildUltrasonicHealth(sensorUltrasonic, 0));
                if (sensorLidar) entries.push_back(buildLidarHealth(sensorLidar));
                out.push_back(static_cast<uint8_t>(entries.size()));
                for (const auto& entry : entries) {
                    out.push_back(entry.kind);
                    out.push_back(entry.sensor_id);
                    out.push_back(entry.flags);
                    out.push_back(entry.detail);
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

            ctx.telemetry->registerBinProvider(
                TelemetrySections::id(TelemetrySections::SectionId::TELEM_ULTRASONIC),
                [ultrasonic](std::vector<uint8_t>& out) {
                    const uint8_t sensor_id = 0;
                    const bool attached = ultrasonic->isAttached(sensor_id);
                    const float dist_cm = attached ? ultrasonic->readDistanceCm(sensor_id) : -1.0f;
                    const bool ok = attached && (dist_cm >= 0.0f);
                    uint16_t dist_mm = ok ? static_cast<uint16_t>(dist_cm * 10.0f) : 0;
                    out.push_back(sensor_id);
                    out.push_back(attached ? 1 : 0);
                    out.push_back(ok ? 1 : 0);
                    out.push_back(static_cast<uint8_t>(dist_mm & 0xFF));
                    out.push_back(static_cast<uint8_t>((dist_mm >> 8) & 0xFF));
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

            ctx.telemetry->registerBinProvider(
                TelemetrySections::id(TelemetrySections::SectionId::TELEM_IMU),
                [imu](std::vector<uint8_t>& out) {
                    const bool online = imu->isOnline();
                    ImuManager::Sample s;
                    const bool ok = online && imu->readSample(s);
                    auto put_i16 = [&out](int16_t v) {
                        out.push_back(static_cast<uint8_t>(v & 0xFF));
                        out.push_back(static_cast<uint8_t>((v >> 8) & 0xFF));
                    };
                    out.push_back(online ? 1 : 0);
                    out.push_back(ok ? 1 : 0);
                    put_i16(ok ? static_cast<int16_t>(s.ax_g * 1000.0f) : 0);
                    put_i16(ok ? static_cast<int16_t>(s.ay_g * 1000.0f) : 0);
                    put_i16(ok ? static_cast<int16_t>(s.az_g * 1000.0f) : 0);
                    put_i16(ok ? static_cast<int16_t>(s.gx_dps * 1000.0f) : 0);
                    put_i16(ok ? static_cast<int16_t>(s.gy_dps * 1000.0f) : 0);
                    put_i16(ok ? static_cast<int16_t>(s.gz_dps * 1000.0f) : 0);
                    put_i16(ok ? static_cast<int16_t>(s.temp_c * 100.0f) : 0);
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

            ctx.telemetry->registerBinProvider(
                TelemetrySections::id(TelemetrySections::SectionId::TELEM_ENCODER0),
                [encoder](std::vector<uint8_t>& out) {
                    int32_t ticks = encoder->getCount(0);
                    out.push_back(static_cast<uint8_t>(ticks & 0xFF));
                    out.push_back(static_cast<uint8_t>((ticks >> 8) & 0xFF));
                    out.push_back(static_cast<uint8_t>((ticks >> 16) & 0xFF));
                    out.push_back(static_cast<uint8_t>((ticks >> 24) & 0xFF));
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

        // Control graph debug values (per-transform intermediate values)
        if (ctx.control) {
            ControlModule* control = ctx.control;
            ctx.telemetry->registerProvider(
                "ctrl_graph_debug",
                [control](ArduinoJson::JsonObject node) {
                    const auto& graph = control->graph();
                    const int8_t debugIdx = graph.debugSlotIdx();
                    node["enabled"] = (debugIdx >= 0);
                    if (debugIdx < 0) return;

                    const char* slotId = graph.debugSlotId();
                    if (slotId) {
                        node["slot_id"] = slotId;
                    }

                    // Get debug values (source + transform outputs + final)
                    float values[ControlGraphRuntime::MAX_TRANSFORMS + 2];
                    uint8_t count = graph.getDebugValues(values, sizeof(values) / sizeof(values[0]));
                    node["count"] = count;

                    ArduinoJson::JsonArray arr = node["values"].to<ArduinoJson::JsonArray>();
                    for (uint8_t i = 0; i < count; ++i) {
                        arr.add(values[i]);
                    }
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
