#include "config/FeatureFlags.h"

#if HAS_IMU

#include "sensor/ImuManager.h"

// MPU-60x0 / MPU-9250 style registers
static constexpr uint8_t REG_PWR_MGMT_1   = 0x6B;
static constexpr uint8_t REG_WHO_AM_I     = 0x75;
static constexpr uint8_t REG_ACCEL_XOUT_H = 0x3B;

// WHO_AM_I expected values (depends on chip, keep both)
static constexpr uint8_t WHO_AM_I_MPU6050 = 0x68;
static constexpr uint8_t WHO_AM_I_MPU6500 = 0x70;
static constexpr uint8_t WHO_AM_I_MPU9250 = 0x71;

bool ImuManager::begin(uint8_t addr) {
    if (!hal_) {
        DBG_PRINTLN("[ImuManager] begin() failed: HAL not set!");
        return false;
    }

    addr_ = addr;
    DBG_PRINTF("[ImuManager] begin() addr=0x%02X\n", addr_);

    // Check if device is present
    if (!hal_->devicePresent(addr_)) {
        DBG_PRINTLN("[ImuManager] Device not found on I2C bus");
        online_ = false;
        return false;
    }

    // Read WHO_AM_I
    uint8_t who = 0;
    hal::I2cResult result = hal_->readReg(addr_, REG_WHO_AM_I, &who);
    if (result != hal::I2cResult::Ok) {
        DBG_PRINTLN("[ImuManager] Failed to read WHO_AM_I");
        online_ = false;
        return false;
    }

    DBG_PRINTF("[ImuManager] WHO_AM_I=0x%02X\n", who);

    if (who != WHO_AM_I_MPU6050 &&
        who != WHO_AM_I_MPU6500 &&
        who != WHO_AM_I_MPU9250) {
        DBG_PRINTLN("[ImuManager] Unexpected WHO_AM_I, IMU may not be connected");
        online_ = false;
        return false;
    }

    // Wake up device: clear sleep bit
    result = hal_->writeReg(addr_, REG_PWR_MGMT_1, 0x00);
    if (result != hal::I2cResult::Ok) {
        DBG_PRINTLN("[ImuManager] Failed to write PWR_MGMT_1");
        online_ = false;
        return false;
    }

    // Small delay for device to wake up
    // Note: In portable code, we'd use hal_->timer->delayMillis(100)
    // For now, use a busy loop or trust the device is fast
    volatile int dummy = 0;
    for (int i = 0; i < 100000; ++i) { dummy++; }

    DBG_PRINTLN("[ImuManager] IMU online and initialized");
    online_ = true;
    return true;
}

bool ImuManager::readSample(Sample& out) {
    if (!online_ || !hal_) {
        return false;
    }

    uint8_t raw[14];
    hal::I2cResult result = hal_->readRegs(addr_, REG_ACCEL_XOUT_H, raw, sizeof(raw));
    if (result != hal::I2cResult::Ok) {
        DBG_PRINTLN("[ImuManager] readRegs failed");
        return false;
    }

    auto toInt16 = [](uint8_t hi, uint8_t lo) -> int16_t {
        return static_cast<int16_t>((hi << 8) | lo);
    };

    int16_t ax_raw   = toInt16(raw[0],  raw[1]);
    int16_t ay_raw   = toInt16(raw[2],  raw[3]);
    int16_t az_raw   = toInt16(raw[4],  raw[5]);
    int16_t temp_raw = toInt16(raw[6],  raw[7]);
    int16_t gx_raw   = toInt16(raw[8],  raw[9]);
    int16_t gy_raw   = toInt16(raw[10], raw[11]);
    int16_t gz_raw   = toInt16(raw[12], raw[13]);

    // Convert to physical units (assuming default config):
    // accel: ±2g → 16384 LSB/g
    // gyro:  ±250 deg/s → 131 LSB/(deg/s)
    out.ax_g = ax_raw / 16384.0f;
    out.ay_g = ay_raw / 16384.0f;
    out.az_g = az_raw / 16384.0f;

    out.gx_dps = gx_raw / 131.0f;
    out.gy_dps = gy_raw / 131.0f;
    out.gz_dps = gz_raw / 131.0f;

    // Temperature for MPU-6050: Temp(°C) = temp_raw/340 + 36.53
    out.temp_c = (temp_raw / 340.0f) + 36.53f;

    return true;
}

#endif // HAS_IMU
