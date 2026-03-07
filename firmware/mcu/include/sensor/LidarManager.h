#pragma once

#include "config/FeatureFlags.h"

#if HAS_LIDAR

#include "hal/II2c.h"
#include "hal/drivers/Vl53l0x.h"
#include "core/Debug.h"
#include <cmath>

/// LiDAR sensor manager using HAL-based VL53L0X driver
/// Fully portable - no platform-specific dependencies
class LidarManager {
public:
    struct Sample {
        float distance_m = NAN;
    };

    static constexpr uint8_t DEFAULT_ADDR = 0x29;

    LidarManager() = default;

    /// Set the HAL I2C driver (must be called before begin)
    void setHal(hal::II2c* i2c) {
        hal_ = i2c;
    }

    /// Initialize LiDAR sensor
    /// I2C bus must already be initialized via HAL
    bool begin(uint8_t addr = DEFAULT_ADDR);

    /// Legacy signature for compatibility (pins ignored, HAL handles I2C init)
    bool begin(uint8_t sdaPin, uint8_t sclPin, uint8_t addr = DEFAULT_ADDR) {
        (void)sdaPin;
        (void)sclPin;
        return begin(addr);
    }

    bool isOnline() const { return online_; }

    bool readSample(Sample& out);

    /// Set measurement timeout in milliseconds
    void setTimeout(uint16_t timeoutMs) {
        lidar_.setTimeout(timeoutMs);
    }

    /// Check if last read timed out
    bool timeoutOccurred() const {
        return lidar_.timeoutOccurred();
    }

private:
    hal::II2c* hal_ = nullptr;
    hal::Vl53l0x lidar_;
    bool online_ = false;
    uint8_t addr_ = DEFAULT_ADDR;
};

#else // !HAS_LIDAR

#include <cmath>

// Stub when LiDAR is disabled
class LidarManager {
public:
    struct Sample {
        float distance_m = NAN;
    };

    static constexpr uint8_t DEFAULT_ADDR = 0x29;

    LidarManager() = default;
    void setHal(void*) {}
    bool begin(uint8_t = DEFAULT_ADDR) { return false; }
    bool begin(uint8_t, uint8_t, uint8_t = DEFAULT_ADDR) { return false; }
    bool isOnline() const { return false; }
    bool readSample(Sample&) { return false; }
    void setTimeout(uint16_t) {}
    bool timeoutOccurred() const { return false; }
};

#endif // HAS_LIDAR
