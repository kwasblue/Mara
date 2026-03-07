#pragma once

#include <cstdint>

namespace mara {

/// Timing instrumentation for main loop phases.
/// Tracks execution time for each phase to identify bottlenecks.
struct LoopTiming {
    // Per-phase timing (microseconds)
    uint32_t safety_us = 0;
    uint32_t control_us = 0;
    uint32_t telemetry_us = 0;
    uint32_t host_us = 0;
    uint32_t total_us = 0;

    // Peak values (max observed)
    uint32_t safety_peak_us = 0;
    uint32_t control_peak_us = 0;
    uint32_t telemetry_peak_us = 0;
    uint32_t host_peak_us = 0;
    uint32_t total_peak_us = 0;

    // Iteration counter
    uint32_t iterations = 0;

    // Overrun counter (loop took longer than target period)
    uint32_t overruns = 0;

    /// Update peak values from current values
    void updatePeaks() {
        if (safety_us > safety_peak_us) safety_peak_us = safety_us;
        if (control_us > control_peak_us) control_peak_us = control_us;
        if (telemetry_us > telemetry_peak_us) telemetry_peak_us = telemetry_us;
        if (host_us > host_peak_us) host_peak_us = host_us;
        if (total_us > total_peak_us) total_peak_us = total_us;
        ++iterations;
    }

    /// Reset all timing data
    void reset() {
        safety_us = control_us = telemetry_us = host_us = total_us = 0;
        safety_peak_us = control_peak_us = telemetry_peak_us = host_peak_us = total_peak_us = 0;
        iterations = 0;
        overruns = 0;
    }
};

/// Global accessor for loop timing
LoopTiming& getLoopTiming();

} // namespace mara
