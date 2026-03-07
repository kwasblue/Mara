#include "config/FeatureFlags.h"

#if HAS_LIDAR

#include "sensor/LidarManager.h"

bool LidarManager::begin(uint8_t addr) {
    if (!hal_) {
        DBG_PRINTLN("[LidarManager] begin() failed: HAL not set!");
        return false;
    }

    addr_ = addr;
    DBG_PRINTF("[LidarManager] begin() addr=0x%02X\n", addr_);

    // Initialize driver with HAL I2C
    if (!lidar_.begin(hal_, addr_)) {
        DBG_PRINTLN("[LidarManager] VL53L0X init failed");
        online_ = false;
        return false;
    }

    // Set timeout
    lidar_.setTimeout(500);

    // Start continuous mode for fast polling
    if (!lidar_.startContinuous()) {
        DBG_PRINTLN("[LidarManager] Failed to start continuous mode");
        online_ = false;
        return false;
    }

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
        DBG_PRINTLN("[LidarManager] VL53L0X timeout");
        return false;
    }

    // Sanity check: 0 or >4m is invalid
    if (mm == 0 || mm > 4000 || mm == 0xFFFF) {
        return false;
    }

    out.distance_m = mm / 1000.0f;
    return true;
}

#endif // HAS_LIDAR
