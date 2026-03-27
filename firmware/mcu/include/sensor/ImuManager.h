#pragma once

#include "config/FeatureFlags.h"

#if HAS_IMU

#include "hal/II2c.h"
#include "core/Debug.h"

class ImuManager {
public:
    struct Sample {
        float ax_g = 0.0f;
        float ay_g = 0.0f;
        float az_g = 0.0f;
        float gx_dps = 0.0f;
        float gy_dps = 0.0f;
        float gz_dps = 0.0f;
        float temp_c = 0.0f;
    };

    enum class DeviceType : uint8_t {
        Unknown = 0,
        Mpu6050,
        Mpu6500,
        Mpu9250,
    };

    ImuManager() = default;

    /// Set the HAL I2C driver (must be called before begin)
    void setHal(hal::II2c* i2c) {
        hal_ = i2c;
    }

    /// Initialize IMU at given address. I2C bus must already be initialized.
    /// Returns true if WHO_AM_I looks OK.
    bool begin(uint8_t addr = 0x68);

    /// Legacy signature for compatibility.
    /// Re-applies the expected bus speed, then probes the requested address and
    /// falls back to the alternate AD0 address if needed.
    bool begin(int sdaPin, int sclPin, uint8_t addr = 0x68);

    bool isOnline() const { return online_; }
    uint8_t address() const { return addr_; }
    hal::II2c* hal() const { return hal_; }
    uint8_t whoAmI() const { return whoAmI_; }
    DeviceType deviceType() const { return deviceType_; }

    /// Read one accel/gyro/temp sample. Returns false if IMU offline or read failed.
    bool readSample(Sample& out);

private:
    hal::II2c* hal_ = nullptr;
    uint8_t addr_ = 0x68;
    uint8_t whoAmI_ = 0;
    DeviceType deviceType_ = DeviceType::Unknown;
    bool online_ = false;
};

#else // !HAS_IMU

// Stub when IMU is disabled
class ImuManager {
public:
    struct Sample {
        float ax_g = 0.0f;
        float ay_g = 0.0f;
        float az_g = 0.0f;
        float gx_dps = 0.0f;
        float gy_dps = 0.0f;
        float gz_dps = 0.0f;
        float temp_c = 0.0f;
    };

    enum class DeviceType : uint8_t {
        Unknown = 0,
        Mpu6050,
        Mpu6500,
        Mpu9250,
    };

    ImuManager() = default;
    void setHal(void*) {}
    bool begin(uint8_t = 0x68) { return false; }
    bool begin(int, int, uint8_t = 0x68) { return false; }
    bool isOnline() const { return false; }
    uint8_t address() const { return 0x68; }
    hal::II2c* hal() const { return nullptr; }
    uint8_t whoAmI() const { return 0; }
    DeviceType deviceType() const { return DeviceType::Unknown; }
    bool readSample(Sample&) { return false; }
};

#endif // HAS_IMU
