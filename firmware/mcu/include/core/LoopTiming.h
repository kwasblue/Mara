#pragma once

#include <cstdint>

namespace mara {

struct LoopTiming {
    uint32_t safety_us = 0;
    uint32_t control_us = 0;
    uint32_t telemetry_us = 0;
    uint32_t host_us = 0;
    uint32_t total_us = 0;

    uint32_t safety_peak_us = 0;
    uint32_t control_peak_us = 0;
    uint32_t telemetry_peak_us = 0;
    uint32_t host_peak_us = 0;
    uint32_t total_peak_us = 0;

    uint32_t iterations = 0;
    uint32_t overruns = 0;

    uint64_t total_runtime_us = 0;
    uint64_t control_runtime_us = 0;
    uint64_t telemetry_runtime_us = 0;
    uint64_t host_runtime_us = 0;

    uint32_t avg_total_us = 0;
    uint32_t avg_control_us = 0;
    uint32_t avg_telemetry_us = 0;
    uint32_t avg_host_us = 0;

    void updatePeaks() {
        if (safety_us > safety_peak_us) safety_peak_us = safety_us;
        if (control_us > control_peak_us) control_peak_us = control_us;
        if (telemetry_us > telemetry_peak_us) telemetry_peak_us = telemetry_us;
        if (host_us > host_peak_us) host_peak_us = host_us;
        if (total_us > total_peak_us) total_peak_us = total_us;
        total_runtime_us += total_us;
        control_runtime_us += control_us;
        telemetry_runtime_us += telemetry_us;
        host_runtime_us += host_us;
        ++iterations;
        avg_total_us = iterations ? static_cast<uint32_t>(total_runtime_us / iterations) : 0;
        avg_control_us = iterations ? static_cast<uint32_t>(control_runtime_us / iterations) : 0;
        avg_telemetry_us = iterations ? static_cast<uint32_t>(telemetry_runtime_us / iterations) : 0;
        avg_host_us = iterations ? static_cast<uint32_t>(host_runtime_us / iterations) : 0;
    }

    void reset() {
        safety_us = control_us = telemetry_us = host_us = total_us = 0;
        safety_peak_us = control_peak_us = telemetry_peak_us = host_peak_us = total_peak_us = 0;
        iterations = 0;
        overruns = 0;
        total_runtime_us = control_runtime_us = telemetry_runtime_us = host_runtime_us = 0;
        avg_total_us = avg_control_us = avg_telemetry_us = avg_host_us = 0;
    }
};

LoopTiming& getLoopTiming();

} // namespace mara
