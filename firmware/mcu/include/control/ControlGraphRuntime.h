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
#include "hw/GpioManager.h"
#include "motor/ServoManager.h"
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
    };

    enum class SinkKind : uint8_t {
        Unsupported = 0,
        GpioWrite,
        ServoAngle,
    };

    struct TransformRuntime {
        TransformKind kind = TransformKind::Unsupported;
        float a = 0.0f;
        float b = 0.0f;
        uint32_t t_ms = 0;
        bool initialized = false;
    };

    struct SlotRuntime {
        bool valid = false;
        SourceKind source = SourceKind::Unsupported;
        SinkKind sink = SinkKind::Unsupported;
        char imu_axis[8] = {0};
        float source_value = 0.0f;
        int sink_channel = -1;
        int sink_servo_id = -1;
        uint8_t transform_count = 0;
        TransformRuntime transforms[MAX_TRANSFORMS]{};
        uint32_t last_run_ms = 0;
        uint32_t run_count = 0;
        bool last_output_high = false;
        char error[24] = {0};
    };

    bool upload(JsonVariantConst graph, const char*& error) {
        if (!uploadInMemory_(graph, error)) {
            return false;
        }
        if (!savePersistedGraph_(graph, error)) {
            clearInMemory_();
            return false;
        }
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

        DynamicJsonDocument doc(static_cast<size_t>(len) + 512u);
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
        }
    }

    void step(uint32_t now_ms, const ModeManager* mode, GpioManager* gpio, ServoManager* servo, ImuManager* imu) {
        if (!present_ || !any_enabled_) return;

        bool mode_ok = true;
        if (mode) {
            const MaraMode current = mode->mode();
            mode_ok = (current == MaraMode::IDLE || current == MaraMode::ARMED || current == MaraMode::ACTIVE);
        }
        if (!mode_ok) return;

        for (uint8_t i = 0; i < slot_count_; ++i) {
            auto& summary = slots_[i];
            auto& slot = runtime_[i];
            if (!summary.enabled || !slot.valid) continue;

            const uint16_t rate_hz = summary.rate_hz > 0 ? summary.rate_hz : 1;
            const uint32_t period_ms = rate_hz >= 1000 ? 1u : (1000u / rate_hz ? 1000u / rate_hz : 1u);
            if (slot.last_run_ms != 0 && (now_ms - slot.last_run_ms) < period_ms) {
                continue;
            }

            float value = 0.0f;
            if (!readSource_(slot, imu, value)) {
                copyString_(slot.error, sizeof(slot.error), "source_read_failed");
                slot.last_run_ms = now_ms;
                continue;
            }

            bool should_emit = true;
            value = applyTransforms_(slot, value, now_ms, should_emit);
            if (should_emit) {
                writeSink_(slot, gpio, servo, value);
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
            JsonObjectConst sink = slot["sink"].as<JsonObjectConst>();
            if (!source || !sink) {
                error = "source_and_sink_required";
                clearInMemory_();
                return false;
            }
            copyString_(out.source_type, sizeof(out.source_type), source["type"] | "");
            copyString_(out.sink_type, sizeof(out.sink_type), sink["type"] | "");

            JsonArrayConst transforms = slot["transforms"].as<JsonArrayConst>();
            out.transform_count = transforms ? static_cast<uint8_t>(transforms.size()) : 0;
            if (out.transform_count > MAX_TRANSFORMS) {
                error = "too_many_transforms";
                clearInMemory_();
                return false;
            }

            if (!parseSlot_(source, transforms, sink, runtime, error)) {
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

    static float computePitchDeg_(const ImuManager::Sample& s) {
        return atan2f(s.ay_g, sqrtf((s.ax_g * s.ax_g) + (s.az_g * s.az_g))) * 57.2957795f;
    }

    static float computeRollDeg_(const ImuManager::Sample& s) {
        return atan2f(-s.ax_g, s.az_g) * 57.2957795f;
    }

    bool parseSlot_(JsonObjectConst source, JsonArrayConst transforms, JsonObjectConst sink, SlotRuntime& out, const char*& error) {
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
        } else {
            error = "unsupported_source";
            return false;
        }

        out.transform_count = 0;
        for (JsonObjectConst transform : transforms) {
            const char* t = transform["type"] | "";
            JsonObjectConst params = transform["params"].as<JsonObjectConst>();
            TransformRuntime& tr = out.transforms[out.transform_count++];

            if (strcmp(t, "scale") == 0) {
                tr.kind = TransformKind::Scale;
                tr.a = params["factor"] | 1.0f;
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
            } else {
                error = "unsupported_transform";
                return false;
            }
        }

        const char* sink_type = sink["type"] | "";
        JsonObjectConst sink_params = sink["params"].as<JsonObjectConst>();
        if (strcmp(sink_type, "gpio_write") == 0) {
            out.sink = SinkKind::GpioWrite;
            out.sink_channel = sink_params["channel"] | -1;
            if (out.sink_channel < 0) {
                error = "invalid_gpio_channel";
                return false;
            }
        } else if (strcmp(sink_type, "servo_angle") == 0) {
            out.sink = SinkKind::ServoAngle;
            out.sink_servo_id = sink_params["servo_id"] | -1;
            if (out.sink_servo_id < 0) {
                error = "invalid_servo_id";
                return false;
            }
        } else {
            error = "unsupported_sink";
            return false;
        }

        out.valid = true;
        return true;
    }

    bool readSource_(const SlotRuntime& slot, ImuManager* imu, float& value) const {
        switch (slot.source) {
            case SourceKind::Constant:
                value = slot.source_value;
                return true;
            case SourceKind::ImuAxis: {
                if (!imu) return false;
                ImuManager::Sample sample;
                if (!imu->readSample(sample)) return false;
                value = (strcmp(slot.imu_axis, "roll") == 0) ? computeRollDeg_(sample) : computePitchDeg_(sample);
                return true;
            }
            default:
                return false;
        }
    }

    float applyTransforms_(SlotRuntime& slot, float value, uint32_t now_ms, bool& should_emit) {
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
                default:
                    break;
            }
        }
        return value;
    }

    void writeSink_(SlotRuntime& slot, GpioManager* gpio, ServoManager* servo, float value) {
        switch (slot.sink) {
            case SinkKind::GpioWrite: {
                if (!gpio) break;
                const bool high = value > 0.5f;
                gpio->write(slot.sink_channel, high ? 1 : 0);
                slot.last_output_high = high;
                break;
            }
            case SinkKind::ServoAngle: {
                if (!servo) break;
                servo->setAngle(slot.sink_servo_id, clamp_(value, 0.0f, 180.0f));
                slot.last_output_high = value > 90.0f;
                break;
            }
            default:
                break;
        }
    }

    bool present_ = false;
    bool any_enabled_ = false;
    uint16_t schema_version_ = 0;
    uint8_t slot_count_ = 0;
    ControlGraphSlotSummary slots_[MAX_SLOTS]{};
    SlotRuntime runtime_[MAX_SLOTS]{};
};
