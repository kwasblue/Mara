#include "config/FeatureFlags.h"

#if HAS_LIDAR

#include "sensor/LidarManager.h"

bool LidarManager::begin(uint8_t addr) {
    if (!hal_) {
        DBG_PRINTLN("[LidarManager] begin() failed: HAL not set!");
        return false;
    }

    // Guard against double-init: calling startContinuous() on already-running
    // VL53L0X may corrupt sensor state
    if (online_) {
        return true;
    }

    addr_ = addr;
    consecutiveTimeouts_ = 0;
    DBG_PRINTF("[LidarManager] begin() addr=0x%02X\n", addr_);

    // Use longer timeout for initialization (sensor may need time to respond)
    lidar_.setTimeout(INIT_TIMEOUT_MS);

    // Initialize driver with HAL I2C
    if (!lidar_.begin(hal_, addr_)) {
        DBG_PRINTLN("[LidarManager] VL53L0X init failed");
        online_ = false;
        return false;
    }

    // Start continuous mode for fast polling
    if (!lidar_.startContinuous()) {
        DBG_PRINTLN("[LidarManager] Failed to start continuous mode");
        online_ = false;
        return false;
    }

    // Switch to shorter runtime timeout to avoid blocking telemetry/heartbeat
    lidar_.setTimeout(RUNTIME_TIMEOUT_MS);

    online_ = true;
    DBG_PRINTLN("[LidarManager] VL53L0X initialized OK (HAL-based driver)");
    return true;
}

bool LidarManager::readSample(Sample& out) {
    if (!online_) {
        return false;
    }

    uint16_t mm = lidar_.readRangeContinuousMillimeters();

    if (lidar_.timeoutOccurred()) {
        consecutiveTimeouts_++;
        DBG_PRINTF("[LidarManager] VL53L0X timeout (%u/%u)\n",
                   consecutiveTimeouts_, MAX_CONSECUTIVE_TIMEOUTS);

        // After N consecutive timeouts, mark sensor offline to stop hammering
        // the I2C bus. Caller must call begin() to reinitialize.
        if (consecutiveTimeouts_ >= MAX_CONSECUTIVE_TIMEOUTS) {
            DBG_PRINTLN("[LidarManager] Too many timeouts, marking offline");
            online_ = false;
        }
        return false;
    }

    // Successful read - reset timeout counter
    consecutiveTimeouts_ = 0;

    // Sanity check: 0 or >4m is invalid (VL53L0X max range is ~2m typical, 4m absolute)
    // Note: mm > 4000 already catches 0xFFFF (65535), so no separate check needed
    if (mm == 0 || mm > 4000) {
        return false;
    }

    out.distance_m = mm / 1000.0f;
    return true;
}

#endif // HAS_LIDAR
