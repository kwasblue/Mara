#pragma once

#include "hal/II2c.h"
#include <cstdint>

namespace hal {

/// HAL-based VL53L0X Time-of-Flight distance sensor driver
/// Provides basic distance measurement functionality without external libraries
class Vl53l0x {
public:
    /// Default I2C address
    static constexpr uint8_t DEFAULT_ADDRESS = 0x29;

    /// Measurement timing budget presets (microseconds)
    enum class TimingBudget : uint32_t {
        Fast   = 20000,   // 20ms - less accurate, faster
        Normal = 33000,   // 33ms - balanced (default)
        Accurate = 200000 // 200ms - most accurate, slower
    };

    Vl53l0x() = default;

    /// Initialize with HAL I2C interface
    /// @param i2c HAL I2C interface (must already be initialized)
    /// @param address I2C address (default 0x29)
    /// @return true if sensor detected and initialized
    bool begin(II2c* i2c, uint8_t address = DEFAULT_ADDRESS);

    /// Check if sensor is initialized and responding
    bool isOnline() const { return online_; }

    /// Get the I2C address
    uint8_t address() const { return addr_; }

    /// Start continuous ranging mode
    /// @return true if successful
    bool startContinuous();

    /// Stop continuous ranging mode
    void stopContinuous();

    /// Read distance in millimeters (continuous mode)
    /// @return distance in mm, or 0xFFFF on error/timeout
    uint16_t readRangeContinuousMillimeters();

    /// Read single distance measurement (blocking)
    /// @return distance in mm, or 0xFFFF on error/timeout
    uint16_t readRangeSingleMillimeters();

    /// Check if a timeout occurred on last read
    bool timeoutOccurred() const { return timeout_; }

    /// Set measurement timeout
    /// @param timeoutMs Timeout in milliseconds
    void setTimeout(uint16_t timeoutMs) { timeoutMs_ = timeoutMs; }

    /// Set timing budget (affects accuracy vs speed)
    /// @param budget Timing budget preset
    /// @return true if successful
    bool setMeasurementTimingBudget(TimingBudget budget);

    /// Set timing budget in microseconds
    /// @param budgetUs Timing budget in microseconds (min 20000)
    /// @return true if successful
    bool setMeasurementTimingBudget(uint32_t budgetUs);

private:
    II2c* i2c_ = nullptr;
    uint8_t addr_ = DEFAULT_ADDRESS;
    bool online_ = false;
    bool timeout_ = false;
    uint16_t timeoutMs_ = 500;
    uint32_t measurementTimingBudgetUs_ = 33000;

    // Cached calibration values
    uint8_t stopVariable_ = 0;

    // Register access helpers
    bool writeReg(uint8_t reg, uint8_t value);
    bool writeReg16(uint8_t reg, uint16_t value);
    bool writeReg32(uint8_t reg, uint32_t value);
    bool writeMulti(uint8_t reg, const uint8_t* data, uint8_t count);
    uint8_t readReg(uint8_t reg);
    uint16_t readReg16(uint8_t reg);
    bool readMulti(uint8_t reg, uint8_t* data, uint8_t count);

    // Initialization helpers
    bool dataInit();
    bool staticInit();
    bool performRefCalibration();
    bool setSequenceSteps();

    // Timing helpers
    uint32_t timeoutMclksToMicroseconds(uint16_t mclks, uint8_t vcselPeriodPclks);
    uint32_t timeoutMicrosecondsToMclks(uint32_t us, uint8_t vcselPeriodPclks);
    uint16_t encodeTimeout(uint32_t mclks);
    uint32_t decodeTimeout(uint16_t encoded);
};

} // namespace hal
