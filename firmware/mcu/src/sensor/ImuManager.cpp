#include "config/FeatureFlags.h"

#if HAS_IMU

#include "sensor/ImuManager.h"
#include "control/SignalBus.h"
#include "core/Clock.h"
#include <math.h>

#include "config/PlatformConfig.h"
#if PLATFORM_HAS_ARDUINO
#include <Arduino.h>
#endif

namespace {
// MPU-60x0 / MPU-9250 / MPU-6500 register set
static constexpr uint8_t REG_SMPLRT_DIV    = 0x19;
static constexpr uint8_t REG_CONFIG        = 0x1A;
static constexpr uint8_t REG_GYRO_CONFIG   = 0x1B;
static constexpr uint8_t REG_ACCEL_CONFIG  = 0x1C;
static constexpr uint8_t REG_ACCEL_CONFIG2 = 0x1D;
static constexpr uint8_t REG_PWR_MGMT_1    = 0x6B;
static constexpr uint8_t REG_WHO_AM_I      = 0x75;
static constexpr uint8_t REG_ACCEL_XOUT_H  = 0x3B;

// WHO_AM_I values seen across MPU60x0 / 65x0 / 92x0 variants.
static constexpr uint8_t WHO_AM_I_MPU6050 = 0x68;
static constexpr uint8_t WHO_AM_I_MPU6500 = 0x70;
static constexpr uint8_t WHO_AM_I_MPU9250 = 0x71;
static constexpr uint8_t WHO_AM_I_ICM20602 = 0x12;
static constexpr uint8_t WHO_AM_I_MPU60X0_CLONE = 0x73;

ImuManager::DeviceType classifyDevice(uint8_t who) {
    switch (who) {
        case WHO_AM_I_MPU6050:
            return ImuManager::DeviceType::Mpu6050;
        case WHO_AM_I_MPU6500:
        case WHO_AM_I_ICM20602:
        case WHO_AM_I_MPU60X0_CLONE:
            return ImuManager::DeviceType::Mpu6500;
        case WHO_AM_I_MPU9250:
            return ImuManager::DeviceType::Mpu9250;
        default:
            return ImuManager::DeviceType::Unknown;
    }
}

bool writeChecked(hal::II2c* hal, uint8_t addr, uint8_t reg, uint8_t value, const char* name) {
    const hal::I2cResult result = hal->writeReg(addr, reg, value);
    if (result != hal::I2cResult::Ok) {
        DBG_PRINTF("[ImuManager] Failed to write %s (0x%02X)\n", name, reg);
        return false;
    }
    return true;
}
} // namespace

bool ImuManager::begin(uint8_t addr) {
    if (!hal_) {
        DBG_PRINTLN("[ImuManager] begin() failed: HAL not set!");
        return false;
    }

    online_ = false;
    deviceType_ = DeviceType::Unknown;
    whoAmI_ = 0;
    addr_ = addr;
    DBG_PRINTF("[ImuManager] begin() addr=0x%02X\n", addr_);

    if (!hal_->devicePresent(addr_)) {
        DBG_PRINTLN("[ImuManager] Device not found on I2C bus");
        return false;
    }

    hal::I2cResult result = hal_->readReg(addr_, REG_WHO_AM_I, &whoAmI_);
    if (result != hal::I2cResult::Ok) {
        DBG_PRINTLN("[ImuManager] Failed to read WHO_AM_I");
        return false;
    }

    DBG_PRINTF("[ImuManager] WHO_AM_I=0x%02X\n", whoAmI_);
    deviceType_ = classifyDevice(whoAmI_);
    if (deviceType_ == DeviceType::Unknown) {
        DBG_PRINTLN("[ImuManager] Unexpected WHO_AM_I, IMU may not be connected");
        return false;
    }

    // Known-good style init sequence:
    // 1) hard wake/reset sleep bit using internal clock
    // 2) short settle delay
    // 3) program sample rate, DLPF, gyro and accel full-scale config
    if (!writeChecked(hal_, addr_, REG_PWR_MGMT_1, 0x00, "PWR_MGMT_1")) {
        return false;
    }
    mara::getSystemClock().delay(100);

    if (!writeChecked(hal_, addr_, REG_SMPLRT_DIV, 0x07, "SMPLRT_DIV")) {
        return false;
    }
    if (!writeChecked(hal_, addr_, REG_CONFIG, 0x06, "CONFIG")) {
        return false;
    }
    if (!writeChecked(hal_, addr_, REG_GYRO_CONFIG, 0x00, "GYRO_CONFIG")) {
        return false;
    }
    if (!writeChecked(hal_, addr_, REG_ACCEL_CONFIG, 0x00, "ACCEL_CONFIG")) {
        return false;
    }
    if (!writeChecked(hal_, addr_, REG_ACCEL_CONFIG2, 0x06, "ACCEL_CONFIG2")) {
        return false;
    }
    mara::getSystemClock().delay(10);

    DBG_PRINTLN("[ImuManager] IMU online and initialized");
    online_ = true;
    return true;
}

bool ImuManager::begin(int sdaPin, int sclPin, uint8_t addr) {
    if (!hal_) {
        DBG_PRINTLN("[ImuManager] begin(pins) failed: HAL not set!");
        return false;
    }

    hal_->begin(static_cast<uint8_t>(sdaPin), static_cast<uint8_t>(sclPin), 400000);
    hal_->setFrequency(400000);

    if (begin(addr)) {
        return true;
    }

    const uint8_t altAddr = (addr == 0x68) ? 0x69 : 0x68;
    if (altAddr != addr) {
        DBG_PRINTF("[ImuManager] Retrying alternate address 0x%02X\n", altAddr);
        return begin(altAddr);
    }
    return false;
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

    out.ax_g = ax_raw / 16384.0f;
    out.ay_g = ay_raw / 16384.0f;
    out.az_g = az_raw / 16384.0f;

    out.gx_dps = gx_raw / 131.0f;
    out.gy_dps = gy_raw / 131.0f;
    out.gz_dps = gz_raw / 131.0f;

    out.temp_c = (temp_raw / 340.0f) + 36.53f;

    return true;
}

// -----------------------------------------------------------------------------
// Auto-Signals Support
// -----------------------------------------------------------------------------

void ImuManager::enableAutoSignals(SignalBus* bus, uint16_t rate_hz) {
    signals_ = bus;
    signalRateHz_ = rate_hz > 0 ? rate_hz : 100;
    lastPublishMs_ = 0;

    if (!bus || signalsDefined_) {
        return;
    }

    // Define auto-signals for IMU readings
    // These use the reserved namespace from SignalNamespace
    bus->defineAutoSignal(SignalNamespace::IMU_AX, "imu.ax", SignalBus::Kind::MEAS, 0.0f);
    bus->defineAutoSignal(SignalNamespace::IMU_AY, "imu.ay", SignalBus::Kind::MEAS, 0.0f);
    bus->defineAutoSignal(SignalNamespace::IMU_AZ, "imu.az", SignalBus::Kind::MEAS, 0.0f);
    bus->defineAutoSignal(SignalNamespace::IMU_GX, "imu.gx", SignalBus::Kind::MEAS, 0.0f);
    bus->defineAutoSignal(SignalNamespace::IMU_GY, "imu.gy", SignalBus::Kind::MEAS, 0.0f);
    bus->defineAutoSignal(SignalNamespace::IMU_GZ, "imu.gz", SignalBus::Kind::MEAS, 0.0f);
    bus->defineAutoSignal(SignalNamespace::IMU_PITCH, "imu.pitch", SignalBus::Kind::EST, 0.0f);
    bus->defineAutoSignal(SignalNamespace::IMU_ROLL, "imu.roll", SignalBus::Kind::EST, 0.0f);

    signalsDefined_ = true;
    DBG_PRINTF("[ImuManager] Auto-signals enabled at %u Hz\n", signalRateHz_);
}

void ImuManager::disableAutoSignals() {
    signals_ = nullptr;
    lastPublishMs_ = 0;
    DBG_PRINTLN("[ImuManager] Auto-signals disabled");
}

void ImuManager::publishToSignals(uint32_t now_ms) {
    if (!signals_ || !online_) {
        return;
    }

    // Rate limiting
    const uint32_t period_ms = signalRateHz_ > 0 ? (1000 / signalRateHz_) : 10;
    if (lastPublishMs_ > 0 && (now_ms - lastPublishMs_) < period_ms) {
        return;
    }

    Sample sample;
    if (!readSample(sample)) {
        return;
    }

    // Publish raw readings
    signals_->setAutoSignal(SignalNamespace::IMU_AX, sample.ax_g, now_ms);
    signals_->setAutoSignal(SignalNamespace::IMU_AY, sample.ay_g, now_ms);
    signals_->setAutoSignal(SignalNamespace::IMU_AZ, sample.az_g, now_ms);
    signals_->setAutoSignal(SignalNamespace::IMU_GX, sample.gx_dps, now_ms);
    signals_->setAutoSignal(SignalNamespace::IMU_GY, sample.gy_dps, now_ms);
    signals_->setAutoSignal(SignalNamespace::IMU_GZ, sample.gz_dps, now_ms);

    // Compute and publish pitch/roll estimates (using accelerometer only)
    const float pitch_deg = atan2f(sample.ay_g, sqrtf(sample.ax_g * sample.ax_g + sample.az_g * sample.az_g)) * 57.2957795f;
    const float roll_deg = atan2f(-sample.ax_g, sample.az_g) * 57.2957795f;
    signals_->setAutoSignal(SignalNamespace::IMU_PITCH, pitch_deg, now_ms);
    signals_->setAutoSignal(SignalNamespace::IMU_ROLL, roll_deg, now_ms);

    lastPublishMs_ = now_ms;
}

#endif // HAS_IMU
