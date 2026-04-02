#pragma once

#include <ArduinoJson.h>
#include <math.h>
#include <stdint.h>
#include <string.h>
#include <vector>

#include <Arduino.h>
#if defined(ARDUINO_ARCH_ESP32)
#include <Preferences.h>
#endif

#include "command/ModeManager.h"
#include "control/SignalBus.h"
#include "hw/GpioManager.h"
#include "motor/ServoManager.h"
#include "sensor/EncoderManager.h"
#include "sensor/ImuManager.h"

struct ControlGraphSlotSummary {
    char id[32] = {0};
    bool enabled = false;
    uint16_t rate_hz = 0;
    char source_type[24] = {0};
    char sink_type[24] = {0};
    uint8_t transform_count = 0;
};

class ControlGraphRuntime {
public:
    static constexpr uint8_t MAX_SLOTS = 8;
    static constexpr uint8_t MAX_TRANSFORMS = 8;

    enum class SourceKind : uint8_t {
        Unsupported = 0,
        Constant,
        ImuAxis,
        SignalRead,
        EncoderVelocity,
    };

    enum class TransformKind : uint8_t {
        Unsupported = 0,
        Scale,
        Offset,
        Clamp,
        Deadband,
        Lowpass,
        DeltaGate,
        SlewRate,
        // New transforms
        Abs,
        Negate,
        Map,
        Hysteresis,
        Median,
        Threshold,
        Toggle,
        Oscillator,
        Pulse,
        Derivative,
        Integrator,
        Proportional,  // Alias for Scale
        // Taps/MISO
        Tap,
        Recall,
        Sum,
        // Signal bus routing
        SignalRecall,
        SignalAdd,
        SignalSubtract,
        Error,
    };

    enum class SinkKind : uint8_t {
        Unsupported = 0,
        GpioWrite,
        ServoAngle,
        SignalWrite,
    };

    struct TransformRuntime {
        TransformKind kind = TransformKind::Unsupported;
        float a = 0.0f;      // Primary param (factor, threshold, min, alpha, freq, etc.)
        float b = 0.0f;      // Secondary param (max, state, phase, prev_value, etc.)
        float c = 0.0f;      // Tertiary param (hysteresis off_threshold, etc.)
        float d = 0.0f;      // Extra state (median buffer sum, etc.)
        uint32_t t_ms = 0;   // Timestamp for time-based transforms
        bool initialized = false;
        bool toggle_state = false;  // For toggle transform
        static constexpr uint8_t MEDIAN_WINDOW = 5;
        float median_buf[MEDIAN_WINDOW] = {0};
        uint8_t median_idx = 0;
        uint8_t median_count = 0;
        // Tap/MISO support
        char tap_name[12] = {0};           // Name for tap/recall
        static constexpr uint8_t MAX_SUM_INPUTS = 4;
        char sum_inputs[MAX_SUM_INPUTS][12] = {{0}};  // Names for sum inputs
        uint8_t sum_input_count = 0;
        // Signal bus routing
        uint16_t signal_id = 0;            // For signal_recall/signal_add
        float signal_fallback = 0.0f;      // Fallback if signal not found
        float signal_scale = 1.0f;         // Scale factor for signal_add
    };

    struct SinkRuntime {
        SinkKind kind = SinkKind::Unsupported;
        int channel = -1;      // For GPIO
        int servo_id = -1;     // For Servo
        uint16_t signal_id = 0; // For SignalWrite
        bool last_output_high = false;
    };

    struct SlotRuntime {
        bool valid = false;
        SourceKind source = SourceKind::Unsupported;
        char imu_axis[8] = {0};
        float source_value = 0.0f;
        uint16_t source_signal_id = 0;      // For SignalRead source
        float source_signal_fallback = 0.0f; // Fallback for SignalRead
        uint8_t encoder_id = 0;              // For EncoderVelocity source
        float encoder_fallback = 0.0f;       // Fallback for EncoderVelocity
        int32_t encoder_last_count = 0;      // Previous encoder count for velocity calc
        uint32_t encoder_last_time_ms = 0;   // Previous timestamp for velocity calc
        float encoder_ticks_per_rad = 1.0f;  // Conversion factor (ticks per radian)
        uint8_t transform_count = 0;
        TransformRuntime transforms[MAX_TRANSFORMS]{};
        uint32_t last_run_ms = 0;
        uint32_t run_count = 0;
        char error[24] = {0};
        // Multi-sink support (SIMO)
        static constexpr uint8_t MAX_SINKS = 4;
        SinkRuntime sinks[MAX_SINKS]{};
        uint8_t sink_count = 0;
        // Tap storage for MISO
        static constexpr uint8_t MAX_TAPS = 8;
        char tap_names[MAX_TAPS][12] = {{0}};
        float tap_values[MAX_TAPS] = {0};
        uint8_t tap_count = 0;
    };

    bool upload(JsonVariantConst graph, const char*& error) {
        // Safety policy: keep control-graph uploads volatile for now.
        // Persisting executable control behavior on the MCU is deferred until
        // we have an explicit operator-controlled restore flow.
        if (!uploadInMemory_(graph, error)) {
            return false;
        }
        clearPersistedGraph_();
        error = nullptr;
        return true;
    }

    bool restore(const char*& error) {
#if defined(ARDUINO_ARCH_ESP32)
        Preferences prefs;
        if (!prefs.begin(kPrefsNamespace, true)) {
            error = "prefs_begin_failed";
            return false;
        }
        const size_t len = prefs.getBytesLength(kPrefsBlobKey);
        if (len == 0) {
            prefs.end();
            error = nullptr;
            return false;
        }
        if (len > kMaxPersistedGraphBytes) {
            prefs.end();
            error = "persisted_graph_too_large";
            return false;
        }

        std::vector<char> buf(len + 1, '\0');
        const size_t actual = prefs.getBytes(kPrefsBlobKey, buf.data(), len);
        prefs.end();
        if (actual != len) {
            error = "persisted_graph_read_failed";
            return false;
        }

        JsonDocument doc;
        const DeserializationError json_error = deserializeJson(doc, buf.data(), len);
        if (json_error) {
            error = "persisted_graph_invalid_json";
            return false;
        }
        return uploadInMemory_(doc.as<JsonVariantConst>(), error);
#else
        error = nullptr;
        return false;
#endif
    }

    void clear() {
        clearInMemory_();
        clearPersistedGraph_();
    }

    void setEnabled(bool enable) {
        any_enabled_ = enable;
        for (uint8_t i = 0; i < slot_count_; ++i) {
            slots_[i].enabled = enable;
            // Reset encoder state on disable to prevent velocity spike on re-enable
            // (avoids garbage spike from large dt_ms when graph was paused)
            if (!enable) {
                runtime_[i].encoder_last_time_ms = 0;
                runtime_[i].encoder_last_count = 0;
            }
        }
    }

    void step(uint32_t now_ms, const ModeManager* mode, GpioManager* gpio, ServoManager* servo, ImuManager* imu, EncoderManager* encoder = nullptr, SignalBus* signals = nullptr) {
        if (!present_ || !any_enabled_) return;

        // Only run control graph when armed or active - IDLE means connected but
        // robot is unarmed, so actuator outputs should not be driven
        bool mode_ok = true;
        if (mode) {
            const MaraMode current = mode->mode();
            mode_ok = (current == MaraMode::ARMED || current == MaraMode::ACTIVE);
        }
        if (!mode_ok) return;

        // Cache IMU sample once per control cycle to avoid multiple I2C reads
        // when multiple slots use IMU sources
        ImuManager::Sample cached_imu_sample{};
        bool imu_sample_valid = false;
        if (imu) {
            imu_sample_valid = imu->readSample(cached_imu_sample);
        }

        for (uint8_t i = 0; i < slot_count_; ++i) {
            auto& summary = slots_[i];
            auto& slot = runtime_[i];
            if (!summary.enabled || !slot.valid) continue;

            const uint16_t rate_hz = summary.rate_hz > 0 ? summary.rate_hz : 100;
            const uint32_t period_ms = rate_hz >= 1000 ? 1u : (1000u / rate_hz ? 1000u / rate_hz : 1u);
            if (slot.last_run_ms != 0 && (now_ms - slot.last_run_ms) < period_ms) {
                continue;
            }

            float value = 0.0f;
            if (!readSource_(slot, cached_imu_sample, imu_sample_valid, encoder, signals, now_ms, value)) {
                copyString_(slot.error, sizeof(slot.error), "source_read_failed");
                slot.last_run_ms = now_ms;
                continue;
            }

            bool should_emit = true;
            value = applyTransforms_(slot, value, now_ms, signals, should_emit);
            if (should_emit) {
                writeSink_(slot, gpio, servo, signals, value);
            }
            slot.last_run_ms = now_ms;
            slot.run_count++;
            slot.error[0] = '\0';
        }
    }

    bool present() const { return present_; }
    bool enabled() const { return any_enabled_; }
    uint16_t schemaVersion() const { return schema_version_; }
    uint8_t slotCount() const { return slot_count_; }
    const ControlGraphSlotSummary& slot(uint8_t idx) const { return slots_[idx]; }
    const SlotRuntime& runtimeSlot(uint8_t idx) const { return runtime_[idx]; }

private:
    static constexpr const char* kPrefsNamespace = "ctrl_graph";
    static constexpr const char* kPrefsBlobKey = "graph_json";
    static constexpr size_t kMaxPersistedGraphBytes = 4096;

    bool uploadInMemory_(JsonVariantConst graph, const char*& error) {
        clearInMemory_();

        if (!graph.is<JsonObjectConst>()) {
            error = "graph_must_be_object";
            return false;
        }

        JsonObjectConst obj = graph.as<JsonObjectConst>();
        schema_version_ = obj["schema_version"] | 0;

        JsonArrayConst slots = obj["slots"].as<JsonArrayConst>();
        if (!slots) {
            error = "slots_required";
            return false;
        }
        if (slots.size() > MAX_SLOTS) {
            error = "too_many_slots";
            return false;
        }

        uint8_t idx = 0;
        for (JsonObjectConst slot : slots) {
            const char* id = slot["id"] | "";
            if (!id[0]) {
                error = "slot_id_required";
                clearInMemory_();
                return false;
            }

            for (uint8_t prev = 0; prev < idx; ++prev) {
                if (strcmp(slots_[prev].id, id) == 0) {
                    error = "duplicate_slot_id";
                    clearInMemory_();
                    return false;
                }
            }

            ControlGraphSlotSummary& out = slots_[idx];
            SlotRuntime& runtime = runtime_[idx];
            copyString_(out.id, sizeof(out.id), id);
            out.enabled = slot["enabled"] | true;
            out.rate_hz = static_cast<uint16_t>(slot["rate_hz"] | 0);

            JsonObjectConst source = slot["source"].as<JsonObjectConst>();
            // Support both single sink (object) and multiple sinks (array)
            JsonVariantConst sinkVariant = slot["sink"].isNull() ? slot["sinks"] : slot["sink"];
            if (!source || sinkVariant.isNull()) {
                error = "source_and_sink_required";
                clearInMemory_();
                return false;
            }
            copyString_(out.source_type, sizeof(out.source_type), source["type"] | "");
            // For summary, show first sink type or "multi" if array
            if (sinkVariant.is<JsonArrayConst>()) {
                JsonArrayConst arr = sinkVariant.as<JsonArrayConst>();
                if (arr.size() > 1) {
                    copyString_(out.sink_type, sizeof(out.sink_type), "multi");
                } else if (arr.size() == 1) {
                    copyString_(out.sink_type, sizeof(out.sink_type), arr[0]["type"] | "");
                }
            } else {
                copyString_(out.sink_type, sizeof(out.sink_type), sinkVariant["type"] | "");
            }

            JsonArrayConst transforms = slot["transforms"].as<JsonArrayConst>();
            out.transform_count = transforms ? static_cast<uint8_t>(transforms.size()) : 0;
            if (out.transform_count > MAX_TRANSFORMS) {
                error = "too_many_transforms";
                clearInMemory_();
                return false;
            }

            if (!parseSlot_(source, transforms, sinkVariant, runtime, error)) {
                clearInMemory_();
                return false;
            }

            ++idx;
        }

        slot_count_ = idx;
        present_ = true;
        any_enabled_ = false;
        for (uint8_t i = 0; i < slot_count_; ++i) {
            any_enabled_ = any_enabled_ || slots_[i].enabled;
        }
        error = nullptr;
        return true;
    }

    void clearInMemory_() {
        present_ = false;
        any_enabled_ = false;
        schema_version_ = 0;
        slot_count_ = 0;
        for (uint8_t i = 0; i < MAX_SLOTS; ++i) {
            slots_[i] = ControlGraphSlotSummary{};
            runtime_[i] = SlotRuntime{};
        }
    }

    bool savePersistedGraph_(JsonVariantConst graph, const char*& error) {
#if defined(ARDUINO_ARCH_ESP32)
        String json;
        serializeJson(graph, json);
        if (json.isEmpty()) {
            error = "persist_graph_serialize_failed";
            return false;
        }
        if (json.length() > kMaxPersistedGraphBytes) {
            error = "persisted_graph_too_large";
            return false;
        }

        Preferences prefs;
        if (!prefs.begin(kPrefsNamespace, false)) {
            error = "prefs_begin_failed";
            return false;
        }
        const size_t written = prefs.putBytes(kPrefsBlobKey, json.c_str(), json.length());
        prefs.end();
        if (written != static_cast<size_t>(json.length())) {
            error = "persist_graph_write_failed";
            return false;
        }
#endif
        error = nullptr;
        return true;
    }

    void clearPersistedGraph_() {
#if defined(ARDUINO_ARCH_ESP32)
        Preferences prefs;
        if (prefs.begin(kPrefsNamespace, false)) {
            prefs.remove(kPrefsBlobKey);
            prefs.end();
        }
#endif
    }

    static void copyString_(char* dst, size_t dst_len, const char* src) {
        if (!dst || dst_len == 0) return;
        if (!src) src = "";
        strncpy(dst, src, dst_len - 1);
        dst[dst_len - 1] = '\0';
    }

    static float clamp_(float v, float lo, float hi) {
        return v < lo ? lo : (v > hi ? hi : v);
    }

    // Tap storage helpers
    static int findTap_(SlotRuntime& slot, const char* name) {
        for (uint8_t i = 0; i < slot.tap_count; ++i) {
            if (strcmp(slot.tap_names[i], name) == 0) return i;
        }
        return -1;
    }

    static bool storeTap_(SlotRuntime& slot, const char* name, float value) {
        int idx = findTap_(slot, name);
        if (idx >= 0) {
            slot.tap_values[idx] = value;
            return true;
        }
        if (slot.tap_count >= SlotRuntime::MAX_TAPS) return false;
        copyString_(slot.tap_names[slot.tap_count], sizeof(slot.tap_names[0]), name);
        slot.tap_values[slot.tap_count] = value;
        slot.tap_count++;
        return true;
    }

    static float recallTap_(SlotRuntime& slot, const char* name, float fallback = 0.0f) {
        int idx = findTap_(slot, name);
        return (idx >= 0) ? slot.tap_values[idx] : fallback;
    }

    static float computePitchDeg_(const ImuManager::Sample& s) {
        return atan2f(s.ay_g, sqrtf((s.ax_g * s.ax_g) + (s.az_g * s.az_g))) * 57.2957795f;
    }

    static float computeRollDeg_(const ImuManager::Sample& s) {
        return atan2f(-s.ax_g, s.az_g) * 57.2957795f;
    }

    bool parseSink_(JsonObjectConst sink, SinkRuntime& out, const char*& error) {
        const char* sink_type = sink["type"] | "";
        JsonObjectConst sink_params = sink["params"].as<JsonObjectConst>();
        if (strcmp(sink_type, "gpio_write") == 0) {
            out.kind = SinkKind::GpioWrite;
            out.channel = sink_params["channel"] | -1;
            if (out.channel < 0) {
                error = "invalid_gpio_channel";
                return false;
            }
        } else if (strcmp(sink_type, "servo_angle") == 0) {
            out.kind = SinkKind::ServoAngle;
            out.servo_id = sink_params["servo_id"] | -1;
            if (out.servo_id < 0) {
                error = "invalid_servo_id";
                return false;
            }
        } else if (strcmp(sink_type, "signal_write") == 0) {
            out.kind = SinkKind::SignalWrite;
            out.signal_id = static_cast<uint16_t>(sink_params["signal_id"] | 0);
        } else {
            error = "unsupported_sink";
            return false;
        }
        return true;
    }

    bool parseSlot_(JsonObjectConst source, JsonArrayConst transforms, JsonVariantConst sinkVariant, SlotRuntime& out, const char*& error) {
        const char* source_type = source["type"] | "";
        JsonObjectConst source_params = source["params"].as<JsonObjectConst>();
        if (strcmp(source_type, "constant") == 0) {
            out.source = SourceKind::Constant;
            out.source_value = source_params["value"] | 0.0f;
        } else if (strcmp(source_type, "imu_axis") == 0) {
            out.source = SourceKind::ImuAxis;
            copyString_(out.imu_axis, sizeof(out.imu_axis), source_params["axis"] | "pitch");
            if (strcmp(out.imu_axis, "pitch") != 0 && strcmp(out.imu_axis, "roll") != 0) {
                error = "unsupported_imu_axis";
                return false;
            }
        } else if (strcmp(source_type, "signal_read") == 0) {
            out.source = SourceKind::SignalRead;
            out.source_signal_id = static_cast<uint16_t>(source_params["signal_id"] | 0);
            out.source_signal_fallback = source_params["fallback"] | 0.0f;
        } else if (strcmp(source_type, "encoder_velocity") == 0) {
            out.source = SourceKind::EncoderVelocity;
            out.encoder_id = static_cast<uint8_t>(source_params["encoder_id"] | 0);
            out.encoder_fallback = source_params["fallback"] | 0.0f;
            out.encoder_ticks_per_rad = source_params["ticks_per_rad"] | 1.0f;
            out.encoder_last_count = 0;
            out.encoder_last_time_ms = 0;
        } else {
            error = "unsupported_source";
            return false;
        }

        out.transform_count = 0;
        for (JsonObjectConst transform : transforms) {
            const char* t = transform["type"] | "";
            JsonObjectConst params = transform["params"].as<JsonObjectConst>();
            TransformRuntime& tr = out.transforms[out.transform_count++];

            if (strcmp(t, "scale") == 0 || strcmp(t, "proportional") == 0) {
                tr.kind = TransformKind::Scale;  // proportional is alias for scale
                tr.a = params["factor"] | (params["gain"] | 1.0f);  // accept either param name
            } else if (strcmp(t, "offset") == 0) {
                tr.kind = TransformKind::Offset;
                tr.a = params["value"] | 0.0f;
            } else if (strcmp(t, "clamp") == 0) {
                tr.kind = TransformKind::Clamp;
                tr.a = params["min"] | -1.0f;
                tr.b = params["max"] | 1.0f;
            } else if (strcmp(t, "deadband") == 0) {
                tr.kind = TransformKind::Deadband;
                tr.a = params["threshold"] | 0.0f;
            } else if (strcmp(t, "lowpass") == 0) {
                tr.kind = TransformKind::Lowpass;
                tr.a = clamp_(params["alpha"] | 0.5f, 0.0f, 1.0f);
                tr.b = 0.0f;
                tr.initialized = false;
            } else if (strcmp(t, "delta_gate") == 0) {
                tr.kind = TransformKind::DeltaGate;
                tr.a = params["threshold"] | 0.0f;
                tr.b = 0.0f;
                tr.initialized = false;
            } else if (strcmp(t, "slew_rate") == 0) {
                tr.kind = TransformKind::SlewRate;
                tr.a = params["rate"] | 0.0f;
                tr.b = 0.0f;
                tr.t_ms = 0;
                tr.initialized = false;
            } else if (strcmp(t, "abs") == 0) {
                tr.kind = TransformKind::Abs;
            } else if (strcmp(t, "negate") == 0) {
                tr.kind = TransformKind::Negate;
            } else if (strcmp(t, "map") == 0) {
                tr.kind = TransformKind::Map;
                tr.a = params["in_min"] | 0.0f;
                tr.b = params["in_max"] | 1.0f;
                tr.c = params["out_min"] | 0.0f;
                tr.d = params["out_max"] | 1.0f;
            } else if (strcmp(t, "hysteresis") == 0) {
                tr.kind = TransformKind::Hysteresis;
                tr.a = params["on_threshold"] | 0.5f;
                tr.c = params["off_threshold"] | 0.3f;
                tr.toggle_state = false;
            } else if (strcmp(t, "median") == 0) {
                tr.kind = TransformKind::Median;
                tr.median_idx = 0;
                tr.median_count = 0;
            } else if (strcmp(t, "threshold") == 0) {
                tr.kind = TransformKind::Threshold;
                tr.a = params["cutoff"] | 0.5f;
                tr.b = params["output_low"] | 0.0f;
                tr.c = params["output_high"] | 1.0f;
            } else if (strcmp(t, "toggle") == 0) {
                tr.kind = TransformKind::Toggle;
                tr.a = params["threshold"] | 0.5f;
                tr.toggle_state = false;
                tr.initialized = false;
            } else if (strcmp(t, "oscillator") == 0) {
                tr.kind = TransformKind::Oscillator;
                tr.a = params["frequency"] | 1.0f;
                tr.b = params["amplitude"] | 1.0f;
                tr.c = params["offset"] | 0.0f;
                tr.d = 0.0f;  // phase
                tr.t_ms = 0;
                tr.initialized = false;
            } else if (strcmp(t, "pulse") == 0) {
                tr.kind = TransformKind::Pulse;
                tr.a = params["interval_ms"] | 1000.0f;
                tr.b = params["duration_ms"] | 100.0f;
                tr.c = params["value"] | 1.0f;
                tr.t_ms = 0;
                tr.initialized = false;
            } else if (strcmp(t, "derivative") == 0) {
                tr.kind = TransformKind::Derivative;
                tr.a = params["gain"] | 1.0f;
                tr.b = 0.0f;  // previous value
                tr.t_ms = 0;
                tr.initialized = false;
            } else if (strcmp(t, "integrator") == 0) {
                tr.kind = TransformKind::Integrator;
                tr.a = params["gain"] | 1.0f;
                tr.b = params["min"] | -1000.0f;  // anti-windup lower bound
                tr.c = params["max"] | 1000.0f;   // anti-windup upper bound
                tr.d = 0.0f;  // accumulated value
                tr.t_ms = 0;
                tr.initialized = false;
            } else if (strcmp(t, "tap") == 0) {
                tr.kind = TransformKind::Tap;
                copyString_(tr.tap_name, sizeof(tr.tap_name), params["name"] | "");
                if (!tr.tap_name[0]) {
                    error = "tap_name_required";
                    return false;
                }
            } else if (strcmp(t, "recall") == 0) {
                tr.kind = TransformKind::Recall;
                copyString_(tr.tap_name, sizeof(tr.tap_name), params["name"] | "");
                if (!tr.tap_name[0]) {
                    error = "recall_name_required";
                    return false;
                }
            } else if (strcmp(t, "sum") == 0) {
                tr.kind = TransformKind::Sum;
                tr.sum_input_count = 0;
                JsonArrayConst inputs = params["inputs"].as<JsonArrayConst>();
                if (!inputs || inputs.size() == 0) {
                    error = "sum_inputs_required";
                    return false;
                }
                for (JsonVariantConst inp : inputs) {
                    if (tr.sum_input_count >= TransformRuntime::MAX_SUM_INPUTS) {
                        error = "too_many_sum_inputs";
                        return false;
                    }
                    const char* name = inp.as<const char*>();
                    if (!name || !name[0]) {
                        error = "sum_input_name_invalid";
                        return false;
                    }
                    copyString_(tr.sum_inputs[tr.sum_input_count], sizeof(tr.sum_inputs[0]), name);
                    tr.sum_input_count++;
                }
            } else if (strcmp(t, "signal_recall") == 0) {
                tr.kind = TransformKind::SignalRecall;
                tr.signal_id = static_cast<uint16_t>(params["signal_id"] | 0);
                tr.signal_fallback = params["fallback"] | 0.0f;
            } else if (strcmp(t, "signal_add") == 0) {
                tr.kind = TransformKind::SignalAdd;
                tr.signal_id = static_cast<uint16_t>(params["signal_id"] | 0);
                tr.signal_fallback = params["fallback"] | 0.0f;
                tr.signal_scale = params["scale"] | 1.0f;
            } else if (strcmp(t, "signal_subtract") == 0) {
                tr.kind = TransformKind::SignalSubtract;
                tr.signal_id = static_cast<uint16_t>(params["signal_id"] | 0);
                tr.signal_fallback = params["fallback"] | 0.0f;
            } else if (strcmp(t, "error") == 0) {
                tr.kind = TransformKind::Error;
                tr.signal_id = static_cast<uint16_t>(params["feedback_signal"] | 0);
                tr.signal_fallback = params["fallback"] | 0.0f;
            } else {
                error = "unsupported_transform";
                return false;
            }
        }

        // Parse sinks (supports single sink object or array of sinks)
        out.sink_count = 0;
        if (sinkVariant.is<JsonArrayConst>()) {
            JsonArrayConst sinks = sinkVariant.as<JsonArrayConst>();
            if (sinks.size() == 0) {
                error = "empty_sinks_array";
                return false;
            }
            if (sinks.size() > SlotRuntime::MAX_SINKS) {
                error = "too_many_sinks";
                return false;
            }
            for (JsonObjectConst s : sinks) {
                if (!parseSink_(s, out.sinks[out.sink_count], error)) {
                    return false;
                }
                out.sink_count++;
            }
        } else if (sinkVariant.is<JsonObjectConst>()) {
            if (!parseSink_(sinkVariant.as<JsonObjectConst>(), out.sinks[0], error)) {
                return false;
            }
            out.sink_count = 1;
        } else {
            error = "sink_must_be_object_or_array";
            return false;
        }

        out.valid = true;
        return true;
    }

    bool readSource_(SlotRuntime& slot, const ImuManager::Sample& cached_imu, bool imu_valid, EncoderManager* encoder, SignalBus* signals, uint32_t now_ms, float& value) {
        switch (slot.source) {
            case SourceKind::Constant:
                value = slot.source_value;
                return true;
            case SourceKind::ImuAxis: {
                // Use cached IMU sample from top of step() to avoid multiple I2C reads
                if (!imu_valid) return false;
                value = (strcmp(slot.imu_axis, "roll") == 0) ? computeRollDeg_(cached_imu) : computePitchDeg_(cached_imu);
                return true;
            }
            case SourceKind::SignalRead: {
                if (!signals) {
                    value = slot.source_signal_fallback;
                    return true;
                }
                if (!signals->get(slot.source_signal_id, value)) {
                    value = slot.source_signal_fallback;
                }
                return true;
            }
            case SourceKind::EncoderVelocity: {
                if (!encoder || !encoder->isAttached(slot.encoder_id)) {
                    value = slot.encoder_fallback;
                    return true;
                }
                const int32_t count = encoder->getCount(slot.encoder_id);
                if (slot.encoder_last_time_ms == 0) {
                    // First read - initialize state
                    slot.encoder_last_count = count;
                    slot.encoder_last_time_ms = now_ms;
                    value = 0.0f;
                    return true;
                }
                const uint32_t dt_ms = (now_ms >= slot.encoder_last_time_ms)
                    ? (now_ms - slot.encoder_last_time_ms) : 1;
                if (dt_ms == 0) {
                    value = 0.0f;
                    return true;
                }
                const int32_t delta = count - slot.encoder_last_count;
                const float dt_s = dt_ms * 0.001f;
                // velocity in rad/s = (delta ticks / ticks_per_rad) / dt_s
                value = (static_cast<float>(delta) / slot.encoder_ticks_per_rad) / dt_s;
                slot.encoder_last_count = count;
                slot.encoder_last_time_ms = now_ms;
                return true;
            }
            default:
                return false;
        }
    }

    float applyTransforms_(SlotRuntime& slot, float value, uint32_t now_ms, SignalBus* signals, bool& should_emit) {
        should_emit = true;
        for (uint8_t i = 0; i < slot.transform_count; ++i) {
            auto& tr = slot.transforms[i];
            switch (tr.kind) {
                case TransformKind::Scale:
                    value *= tr.a;
                    break;
                case TransformKind::Offset:
                    value += tr.a;
                    break;
                case TransformKind::Clamp:
                    value = clamp_(value, tr.a, tr.b);
                    break;
                case TransformKind::Deadband:
                    if (fabsf(value) < tr.a) value = 0.0f;
                    break;
                case TransformKind::Lowpass:
                    if (!tr.initialized) {
                        tr.b = value;
                        tr.initialized = true;
                    } else {
                        tr.b = tr.b + tr.a * (value - tr.b);
                    }
                    value = tr.b;
                    break;
                case TransformKind::DeltaGate:
                    if (!tr.initialized) {
                        tr.b = value;
                        tr.initialized = true;
                    } else if (fabsf(value - tr.b) >= tr.a) {
                        tr.b = value;
                    } else {
                        should_emit = false;
                    }
                    value = tr.b;
                    break;
                case TransformKind::SlewRate:
                    if (!tr.initialized) {
                        tr.b = value;
                        tr.t_ms = now_ms;
                        tr.initialized = true;
                    } else {
                        const uint32_t dt_ms = (now_ms >= tr.t_ms) ? (now_ms - tr.t_ms) : 0;
                        const float dt_s = dt_ms * 0.001f;
                        const float max_delta = tr.a * dt_s;
                        const float delta = value - tr.b;
                        if (max_delta <= 0.0f) {
                            value = tr.b;
                        } else if (delta > max_delta) {
                            tr.b += max_delta;
                            value = tr.b;
                        } else if (delta < -max_delta) {
                            tr.b -= max_delta;
                            value = tr.b;
                        } else {
                            tr.b = value;
                        }
                        tr.t_ms = now_ms;
                    }
                    value = tr.b;
                    break;
                case TransformKind::Abs:
                    value = fabsf(value);
                    break;
                case TransformKind::Negate:
                    value = -value;
                    break;
                case TransformKind::Map: {
                    // Linear interpolation: map [in_min, in_max] to [out_min, out_max]
                    const float in_min = tr.a, in_max = tr.b;
                    const float out_min = tr.c, out_max = tr.d;
                    const float in_range = in_max - in_min;
                    if (fabsf(in_range) < 1e-6f) {
                        value = out_min;
                    } else {
                        value = out_min + (value - in_min) * (out_max - out_min) / in_range;
                    }
                    break;
                }
                case TransformKind::Hysteresis: {
                    // Schmitt trigger: on_threshold (a), off_threshold (c)
                    if (tr.toggle_state) {
                        if (value < tr.c) tr.toggle_state = false;
                    } else {
                        if (value > tr.a) tr.toggle_state = true;
                    }
                    value = tr.toggle_state ? 1.0f : 0.0f;
                    break;
                }
                case TransformKind::Median: {
                    // Rolling median filter
                    tr.median_buf[tr.median_idx] = value;
                    tr.median_idx = (tr.median_idx + 1) % TransformRuntime::MEDIAN_WINDOW;
                    if (tr.median_count < TransformRuntime::MEDIAN_WINDOW) tr.median_count++;

                    // Sort copy to find median
                    float sorted[TransformRuntime::MEDIAN_WINDOW];
                    for (uint8_t j = 0; j < tr.median_count; ++j) sorted[j] = tr.median_buf[j];
                    for (uint8_t j = 0; j < tr.median_count - 1; ++j) {
                        for (uint8_t k = j + 1; k < tr.median_count; ++k) {
                            if (sorted[k] < sorted[j]) {
                                const float tmp = sorted[j];
                                sorted[j] = sorted[k];
                                sorted[k] = tmp;
                            }
                        }
                    }
                    value = sorted[tr.median_count / 2];
                    break;
                }
                case TransformKind::Threshold:
                    // Binary output: output_low (b) if below cutoff (a), output_high (c) otherwise
                    value = (value >= tr.a) ? tr.c : tr.b;
                    break;
                case TransformKind::Toggle: {
                    // Toggle state when input crosses threshold
                    const bool above = value >= tr.a;
                    if (!tr.initialized) {
                        tr.initialized = true;
                        tr.b = above ? 1.0f : 0.0f;  // track previous above state
                    } else {
                        const bool was_above = tr.b > 0.5f;
                        if (above && !was_above) {
                            tr.toggle_state = !tr.toggle_state;
                        }
                        tr.b = above ? 1.0f : 0.0f;
                    }
                    value = tr.toggle_state ? 1.0f : 0.0f;
                    break;
                }
                case TransformKind::Oscillator: {
                    // Sine wave generator: freq (a), amplitude (b), offset (c), phase (d)
                    if (!tr.initialized) {
                        tr.t_ms = now_ms;
                        tr.d = 0.0f;
                        tr.initialized = true;
                    }
                    const uint32_t dt_ms = (now_ms >= tr.t_ms) ? (now_ms - tr.t_ms) : 0;
                    tr.d += tr.a * dt_ms * 0.001f * 2.0f * 3.14159265f;  // phase += freq * dt * 2π
                    if (tr.d > 6.28318530f) tr.d -= 6.28318530f;
                    tr.t_ms = now_ms;
                    value = tr.c + tr.b * sinf(tr.d);
                    break;
                }
                case TransformKind::Pulse: {
                    // Emit pulses: interval_ms (a), duration_ms (b), value (c)
                    if (!tr.initialized) {
                        tr.t_ms = now_ms;
                        tr.initialized = true;
                    }
                    const uint32_t elapsed = (now_ms >= tr.t_ms) ? (now_ms - tr.t_ms) : 0;
                    const uint32_t interval = static_cast<uint32_t>(tr.a);
                    const uint32_t duration = static_cast<uint32_t>(tr.b);
                    const uint32_t phase = interval > 0 ? (elapsed % interval) : 0;
                    value = (phase < duration) ? tr.c : 0.0f;
                    break;
                }
                case TransformKind::Derivative: {
                    // Rate of change: gain (a), prev_value (b)
                    if (!tr.initialized) {
                        tr.b = value;
                        tr.t_ms = now_ms;
                        tr.initialized = true;
                        value = 0.0f;
                    } else {
                        const uint32_t dt_ms = (now_ms >= tr.t_ms) ? (now_ms - tr.t_ms) : 1;
                        const float dt_s = dt_ms * 0.001f;
                        const float dv = value - tr.b;
                        tr.b = value;
                        tr.t_ms = now_ms;
                        value = (dt_s > 0.0f) ? (tr.a * dv / dt_s) : 0.0f;
                    }
                    break;
                }
                case TransformKind::Integrator: {
                    // Accumulate input over time: gain (a), min (b), max (c), accumulated (d)
                    if (!tr.initialized) {
                        tr.d = 0.0f;
                        tr.t_ms = now_ms;
                        tr.initialized = true;
                    } else {
                        const uint32_t dt_ms = (now_ms >= tr.t_ms) ? (now_ms - tr.t_ms) : 1;
                        const float dt_s = dt_ms * 0.001f;
                        tr.d += tr.a * value * dt_s;
                        // Anti-windup clamping
                        tr.d = clamp_(tr.d, tr.b, tr.c);
                        tr.t_ms = now_ms;
                    }
                    value = tr.d;
                    break;
                }
                case TransformKind::Tap:
                    // Save current value to named storage, pass through unchanged
                    storeTap_(slot, tr.tap_name, value);
                    break;
                case TransformKind::Recall:
                    // Replace pipeline value with stored tap
                    value = recallTap_(slot, tr.tap_name, value);
                    break;
                case TransformKind::Sum: {
                    // Sum multiple stored tap values
                    float sum = 0.0f;
                    for (uint8_t j = 0; j < tr.sum_input_count; ++j) {
                        sum += recallTap_(slot, tr.sum_inputs[j], 0.0f);
                    }
                    value = sum;
                    break;
                }
                case TransformKind::SignalRecall: {
                    // Replace current value with signal bus value
                    if (signals) {
                        float sig_val;
                        if (signals->get(tr.signal_id, sig_val)) {
                            value = sig_val;
                        } else {
                            value = tr.signal_fallback;
                        }
                    } else {
                        value = tr.signal_fallback;
                    }
                    break;
                }
                case TransformKind::SignalAdd: {
                    // Add signal bus value to current value (with optional scale)
                    if (signals) {
                        float sig_val;
                        if (signals->get(tr.signal_id, sig_val)) {
                            value += sig_val * tr.signal_scale;
                        } else {
                            value += tr.signal_fallback * tr.signal_scale;
                        }
                    } else {
                        value += tr.signal_fallback * tr.signal_scale;
                    }
                    break;
                }
                case TransformKind::SignalSubtract: {
                    // Subtract signal bus value from current value
                    if (signals) {
                        float sig_val;
                        if (signals->get(tr.signal_id, sig_val)) {
                            value -= sig_val;
                        } else {
                            value -= tr.signal_fallback;
                        }
                    } else {
                        value -= tr.signal_fallback;
                    }
                    break;
                }
                case TransformKind::Error: {
                    // Control error: current (setpoint) - feedback signal
                    float feedback = tr.signal_fallback;
                    if (signals) {
                        float sig_val;
                        if (signals->get(tr.signal_id, sig_val)) {
                            feedback = sig_val;
                        }
                    }
                    value = value - feedback;
                    break;
                }
                default:
                    break;
            }
        }
        return value;
    }

    void writeSink_(SlotRuntime& slot, GpioManager* gpio, ServoManager* servo, SignalBus* signals, float value) {
        for (uint8_t i = 0; i < slot.sink_count; ++i) {
            SinkRuntime& sink = slot.sinks[i];
            switch (sink.kind) {
                case SinkKind::GpioWrite: {
                    if (!gpio) break;
                    const bool high = value > 0.5f;
                    gpio->write(sink.channel, high ? 1 : 0);
                    sink.last_output_high = high;
                    break;
                }
                case SinkKind::ServoAngle: {
                    if (!servo) break;
                    servo->setAngle(sink.servo_id, clamp_(value, 0.0f, 180.0f));
                    sink.last_output_high = value > 90.0f;
                    break;
                }
                case SinkKind::SignalWrite: {
                    if (!signals) break;
                    signals->set(sink.signal_id, value);
                    sink.last_output_high = value > 0.5f;
                    break;
                }
                default:
                    break;
            }
        }
    }

    bool present_ = false;
    bool any_enabled_ = false;
    uint16_t schema_version_ = 0;
    uint8_t slot_count_ = 0;
    ControlGraphSlotSummary slots_[MAX_SLOTS]{};
    SlotRuntime runtime_[MAX_SLOTS]{};
};
