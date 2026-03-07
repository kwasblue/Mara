#include "hal/drivers/Vl53l0x.h"

namespace hal {

// VL53L0X Register addresses
namespace Reg {
    constexpr uint8_t SYSRANGE_START                        = 0x00;
    constexpr uint8_t SYSTEM_THRESH_HIGH                    = 0x0C;
    constexpr uint8_t SYSTEM_THRESH_LOW                     = 0x0E;
    constexpr uint8_t SYSTEM_SEQUENCE_CONFIG                = 0x01;
    constexpr uint8_t SYSTEM_RANGE_CONFIG                   = 0x09;
    constexpr uint8_t SYSTEM_INTERMEASUREMENT_PERIOD        = 0x04;
    constexpr uint8_t SYSTEM_INTERRUPT_CONFIG_GPIO          = 0x0A;
    constexpr uint8_t GPIO_HV_MUX_ACTIVE_HIGH               = 0x84;
    constexpr uint8_t SYSTEM_INTERRUPT_CLEAR                = 0x0B;
    constexpr uint8_t RESULT_INTERRUPT_STATUS               = 0x13;
    constexpr uint8_t RESULT_RANGE_STATUS                   = 0x14;
    constexpr uint8_t RESULT_CORE_AMBIENT_WINDOW_EVENTS_RTN = 0xBC;
    constexpr uint8_t RESULT_CORE_RANGING_TOTAL_EVENTS_RTN  = 0xC0;
    constexpr uint8_t RESULT_CORE_AMBIENT_WINDOW_EVENTS_REF = 0xD0;
    constexpr uint8_t RESULT_CORE_RANGING_TOTAL_EVENTS_REF  = 0xD4;
    constexpr uint8_t RESULT_PEAK_SIGNAL_RATE_REF           = 0xB6;
    constexpr uint8_t ALGO_PART_TO_PART_RANGE_OFFSET_MM     = 0x28;
    constexpr uint8_t I2C_SLAVE_DEVICE_ADDRESS              = 0x8A;
    constexpr uint8_t MSRC_CONFIG_CONTROL                   = 0x60;
    constexpr uint8_t PRE_RANGE_CONFIG_MIN_SNR              = 0x27;
    constexpr uint8_t PRE_RANGE_CONFIG_VALID_PHASE_LOW      = 0x56;
    constexpr uint8_t PRE_RANGE_CONFIG_VALID_PHASE_HIGH     = 0x57;
    constexpr uint8_t PRE_RANGE_MIN_COUNT_RATE_RTN_LIMIT    = 0x64;
    constexpr uint8_t FINAL_RANGE_CONFIG_MIN_SNR            = 0x67;
    constexpr uint8_t FINAL_RANGE_CONFIG_VALID_PHASE_LOW    = 0x47;
    constexpr uint8_t FINAL_RANGE_CONFIG_VALID_PHASE_HIGH   = 0x48;
    constexpr uint8_t FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT = 0x44;
    constexpr uint8_t PRE_RANGE_CONFIG_SIGMA_THRESH_HI      = 0x61;
    constexpr uint8_t PRE_RANGE_CONFIG_SIGMA_THRESH_LO      = 0x62;
    constexpr uint8_t PRE_RANGE_CONFIG_VCSEL_PERIOD         = 0x50;
    constexpr uint8_t PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI    = 0x51;
    constexpr uint8_t PRE_RANGE_CONFIG_TIMEOUT_MACROP_LO    = 0x52;
    constexpr uint8_t SYSTEM_HISTOGRAM_BIN                  = 0x81;
    constexpr uint8_t HISTOGRAM_CONFIG_INITIAL_PHASE_SELECT = 0x33;
    constexpr uint8_t HISTOGRAM_CONFIG_READOUT_CTRL         = 0x55;
    constexpr uint8_t FINAL_RANGE_CONFIG_VCSEL_PERIOD       = 0x70;
    constexpr uint8_t FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI  = 0x71;
    constexpr uint8_t FINAL_RANGE_CONFIG_TIMEOUT_MACROP_LO  = 0x72;
    constexpr uint8_t CROSSTALK_COMPENSATION_PEAK_RATE_MCPS = 0x20;
    constexpr uint8_t MSRC_CONFIG_TIMEOUT_MACROP            = 0x46;
    constexpr uint8_t SOFT_RESET_GO2_SOFT_RESET_N           = 0xBF;
    constexpr uint8_t IDENTIFICATION_MODEL_ID               = 0xC0;
    constexpr uint8_t IDENTIFICATION_REVISION_ID            = 0xC2;
    constexpr uint8_t OSC_CALIBRATE_VAL                     = 0xF8;
    constexpr uint8_t GLOBAL_CONFIG_VCSEL_WIDTH             = 0x32;
    constexpr uint8_t GLOBAL_CONFIG_SPAD_ENABLES_REF_0      = 0xB0;
    constexpr uint8_t GLOBAL_CONFIG_SPAD_ENABLES_REF_1      = 0xB1;
    constexpr uint8_t GLOBAL_CONFIG_SPAD_ENABLES_REF_2      = 0xB2;
    constexpr uint8_t GLOBAL_CONFIG_SPAD_ENABLES_REF_3      = 0xB3;
    constexpr uint8_t GLOBAL_CONFIG_SPAD_ENABLES_REF_4      = 0xB4;
    constexpr uint8_t GLOBAL_CONFIG_SPAD_ENABLES_REF_5      = 0xB5;
    constexpr uint8_t GLOBAL_CONFIG_REF_EN_START_SELECT     = 0xB6;
    constexpr uint8_t DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD   = 0x4E;
    constexpr uint8_t DYNAMIC_SPAD_REF_EN_START_OFFSET      = 0x4F;
    constexpr uint8_t POWER_MANAGEMENT_GO1_POWER_FORCE      = 0x80;
    constexpr uint8_t VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV     = 0x89;
    constexpr uint8_t ALGO_PHASECAL_LIM                     = 0x30;
    constexpr uint8_t ALGO_PHASECAL_CONFIG_TIMEOUT          = 0x30;
}

// ============================================================================
// Register access helpers
// ============================================================================

bool Vl53l0x::writeReg(uint8_t reg, uint8_t value) {
    return i2c_->writeReg(addr_, reg, value) == I2cResult::Ok;
}

bool Vl53l0x::writeReg16(uint8_t reg, uint16_t value) {
    uint8_t data[2] = { (uint8_t)(value >> 8), (uint8_t)(value & 0xFF) };
    uint8_t buf[3] = { reg, data[0], data[1] };
    return i2c_->write(addr_, buf, 3) == I2cResult::Ok;
}

bool Vl53l0x::writeReg32(uint8_t reg, uint32_t value) {
    uint8_t buf[5] = {
        reg,
        (uint8_t)((value >> 24) & 0xFF),
        (uint8_t)((value >> 16) & 0xFF),
        (uint8_t)((value >> 8) & 0xFF),
        (uint8_t)(value & 0xFF)
    };
    return i2c_->write(addr_, buf, 5) == I2cResult::Ok;
}

bool Vl53l0x::writeMulti(uint8_t reg, const uint8_t* data, uint8_t count) {
    // Write register address followed by data
    uint8_t buf[33];  // Max 32 bytes + 1 for register
    if (count > 32) return false;
    buf[0] = reg;
    for (uint8_t i = 0; i < count; i++) {
        buf[i + 1] = data[i];
    }
    return i2c_->write(addr_, buf, count + 1) == I2cResult::Ok;
}

uint8_t Vl53l0x::readReg(uint8_t reg) {
    uint8_t value = 0;
    i2c_->readReg(addr_, reg, &value);
    return value;
}

uint16_t Vl53l0x::readReg16(uint8_t reg) {
    uint8_t data[2] = {0, 0};
    i2c_->readRegs(addr_, reg, data, 2);
    return ((uint16_t)data[0] << 8) | data[1];
}

bool Vl53l0x::readMulti(uint8_t reg, uint8_t* data, uint8_t count) {
    return i2c_->readRegs(addr_, reg, data, count) == I2cResult::Ok;
}

// ============================================================================
// Timing helpers
// ============================================================================

uint32_t Vl53l0x::timeoutMclksToMicroseconds(uint16_t mclks, uint8_t vcselPeriodPclks) {
    uint32_t macroPeriodNs = (((uint32_t)2304 * (vcselPeriodPclks) * 1655) + 500) / 1000;
    return ((mclks * macroPeriodNs) + 500) / 1000;
}

uint32_t Vl53l0x::timeoutMicrosecondsToMclks(uint32_t us, uint8_t vcselPeriodPclks) {
    uint32_t macroPeriodNs = (((uint32_t)2304 * (vcselPeriodPclks) * 1655) + 500) / 1000;
    return (((us) * 1000) + (macroPeriodNs / 2)) / macroPeriodNs;
}

uint16_t Vl53l0x::encodeTimeout(uint32_t mclks) {
    if (mclks == 0) return 0;
    uint32_t lsb = mclks - 1;
    uint16_t msb = 0;
    while ((lsb & 0xFFFFFF00) > 0) {
        lsb >>= 1;
        msb++;
    }
    return (msb << 8) | (uint16_t)(lsb & 0xFF);
}

uint32_t Vl53l0x::decodeTimeout(uint16_t encoded) {
    return ((uint32_t)(encoded & 0xFF) << ((encoded >> 8) & 0xFF)) + 1;
}

// ============================================================================
// Initialization
// ============================================================================

bool Vl53l0x::begin(II2c* i2c, uint8_t address) {
    i2c_ = i2c;
    addr_ = address;
    online_ = false;

    if (!i2c_) return false;

    // Check device ID
    uint8_t id = readReg(Reg::IDENTIFICATION_MODEL_ID);
    if (id != 0xEE) {
        return false;  // Not a VL53L0X
    }

    // Data init
    if (!dataInit()) return false;

    // Static init
    if (!staticInit()) return false;

    // Perform reference calibration
    if (!performRefCalibration()) return false;

    online_ = true;
    return true;
}

bool Vl53l0x::dataInit() {
    // Set 2.8V I/O mode
    writeReg(Reg::VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV,
             readReg(Reg::VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV) | 0x01);

    // Set I2C standard mode
    writeReg(0x88, 0x00);
    writeReg(0x80, 0x01);
    writeReg(0xFF, 0x01);
    writeReg(0x00, 0x00);
    stopVariable_ = readReg(0x91);
    writeReg(0x00, 0x01);
    writeReg(0xFF, 0x00);
    writeReg(0x80, 0x00);

    // Disable SIGNAL_RATE_MSRC and SIGNAL_RATE_PRE_RANGE limit checks
    writeReg(Reg::MSRC_CONFIG_CONTROL, readReg(Reg::MSRC_CONFIG_CONTROL) | 0x12);

    // Set signal rate limit to 0.25 MCPS
    writeReg16(Reg::FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT, 32); // 0.25 * 128

    writeReg(Reg::SYSTEM_SEQUENCE_CONFIG, 0xFF);

    return true;
}

bool Vl53l0x::staticInit() {
    // SPAD calibration
    uint8_t spadCount;
    bool spadTypeIsAperture;

    writeReg(0x80, 0x01);
    writeReg(0xFF, 0x01);
    writeReg(0x00, 0x00);
    writeReg(0xFF, 0x06);
    writeReg(0x83, readReg(0x83) | 0x04);
    writeReg(0xFF, 0x07);
    writeReg(0x81, 0x01);
    writeReg(0x80, 0x01);
    writeReg(0x94, 0x6B);
    writeReg(0x83, 0x00);

    // Wait for completion
    uint32_t start = 0; // Would use timer here
    while (readReg(0x83) == 0x00) {
        if (++start > 10000) return false;
    }

    writeReg(0x83, 0x01);
    uint8_t tmp = readReg(0x92);
    spadCount = tmp & 0x7F;
    spadTypeIsAperture = (tmp >> 7) & 0x01;

    writeReg(0x81, 0x00);
    writeReg(0xFF, 0x06);
    writeReg(0x83, readReg(0x83) & ~0x04);
    writeReg(0xFF, 0x01);
    writeReg(0x00, 0x01);
    writeReg(0xFF, 0x00);
    writeReg(0x80, 0x00);

    // Apply SPAD settings
    uint8_t refSpadMap[6];
    readMulti(Reg::GLOBAL_CONFIG_SPAD_ENABLES_REF_0, refSpadMap, 6);

    writeReg(0xFF, 0x01);
    writeReg(Reg::DYNAMIC_SPAD_REF_EN_START_OFFSET, 0x00);
    writeReg(Reg::DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD, 0x2C);
    writeReg(0xFF, 0x00);
    writeReg(Reg::GLOBAL_CONFIG_REF_EN_START_SELECT, 0xB4);

    uint8_t firstSpadToEnable = spadTypeIsAperture ? 12 : 0;
    uint8_t spadsEnabled = 0;

    for (uint8_t i = 0; i < 48; i++) {
        if (i < firstSpadToEnable || spadsEnabled == spadCount) {
            refSpadMap[i / 8] &= ~(1 << (i % 8));
        } else if ((refSpadMap[i / 8] >> (i % 8)) & 0x01) {
            spadsEnabled++;
        }
    }

    writeMulti(Reg::GLOBAL_CONFIG_SPAD_ENABLES_REF_0, refSpadMap, 6);

    // Load default tuning settings
    writeReg(0xFF, 0x01);
    writeReg(0x00, 0x00);
    writeReg(0xFF, 0x00);
    writeReg(0x09, 0x00);
    writeReg(0x10, 0x00);
    writeReg(0x11, 0x00);
    writeReg(0x24, 0x01);
    writeReg(0x25, 0xFF);
    writeReg(0x75, 0x00);
    writeReg(0xFF, 0x01);
    writeReg(0x4E, 0x2C);
    writeReg(0x48, 0x00);
    writeReg(0x30, 0x20);
    writeReg(0xFF, 0x00);
    writeReg(0x30, 0x09);
    writeReg(0x54, 0x00);
    writeReg(0x31, 0x04);
    writeReg(0x32, 0x03);
    writeReg(0x40, 0x83);
    writeReg(0x46, 0x25);
    writeReg(0x60, 0x00);
    writeReg(0x27, 0x00);
    writeReg(0x50, 0x06);
    writeReg(0x51, 0x00);
    writeReg(0x52, 0x96);
    writeReg(0x56, 0x08);
    writeReg(0x57, 0x30);
    writeReg(0x61, 0x00);
    writeReg(0x62, 0x00);
    writeReg(0x64, 0x00);
    writeReg(0x65, 0x00);
    writeReg(0x66, 0xA0);
    writeReg(0xFF, 0x01);
    writeReg(0x22, 0x32);
    writeReg(0x47, 0x14);
    writeReg(0x49, 0xFF);
    writeReg(0x4A, 0x00);
    writeReg(0xFF, 0x00);
    writeReg(0x7A, 0x0A);
    writeReg(0x7B, 0x00);
    writeReg(0x78, 0x21);
    writeReg(0xFF, 0x01);
    writeReg(0x23, 0x34);
    writeReg(0x42, 0x00);
    writeReg(0x44, 0xFF);
    writeReg(0x45, 0x26);
    writeReg(0x46, 0x05);
    writeReg(0x40, 0x40);
    writeReg(0x0E, 0x06);
    writeReg(0x20, 0x1A);
    writeReg(0x43, 0x40);
    writeReg(0xFF, 0x00);
    writeReg(0x34, 0x03);
    writeReg(0x35, 0x44);
    writeReg(0xFF, 0x01);
    writeReg(0x31, 0x04);
    writeReg(0x4B, 0x09);
    writeReg(0x4C, 0x05);
    writeReg(0x4D, 0x04);
    writeReg(0xFF, 0x00);
    writeReg(0x44, 0x00);
    writeReg(0x45, 0x20);
    writeReg(0x47, 0x08);
    writeReg(0x48, 0x28);
    writeReg(0x67, 0x00);
    writeReg(0x70, 0x04);
    writeReg(0x71, 0x01);
    writeReg(0x72, 0xFE);
    writeReg(0x76, 0x00);
    writeReg(0x77, 0x00);
    writeReg(0xFF, 0x01);
    writeReg(0x0D, 0x01);
    writeReg(0xFF, 0x00);
    writeReg(0x80, 0x01);
    writeReg(0x01, 0xF8);
    writeReg(0xFF, 0x01);
    writeReg(0x8E, 0x01);
    writeReg(0x00, 0x01);
    writeReg(0xFF, 0x00);
    writeReg(0x80, 0x00);

    // Set interrupt config
    writeReg(Reg::SYSTEM_INTERRUPT_CONFIG_GPIO, 0x04);
    writeReg(Reg::GPIO_HV_MUX_ACTIVE_HIGH, readReg(Reg::GPIO_HV_MUX_ACTIVE_HIGH) & ~0x10);
    writeReg(Reg::SYSTEM_INTERRUPT_CLEAR, 0x01);

    // Set default measurement timing budget (33ms)
    setMeasurementTimingBudget(33000);

    // Enable sequence steps
    writeReg(Reg::SYSTEM_SEQUENCE_CONFIG, 0xE8);

    return true;
}

bool Vl53l0x::performRefCalibration() {
    // VHV calibration
    writeReg(Reg::SYSTEM_SEQUENCE_CONFIG, 0x01);
    if (!writeReg(Reg::SYSRANGE_START, 0x01 | 0x40)) return false;

    uint32_t count = 0;
    while ((readReg(Reg::RESULT_INTERRUPT_STATUS) & 0x07) == 0) {
        if (++count > 100000) return false;
    }

    writeReg(Reg::SYSTEM_INTERRUPT_CLEAR, 0x01);
    writeReg(Reg::SYSRANGE_START, 0x00);

    // Phase calibration
    writeReg(Reg::SYSTEM_SEQUENCE_CONFIG, 0x02);
    if (!writeReg(Reg::SYSRANGE_START, 0x01 | 0x40)) return false;

    count = 0;
    while ((readReg(Reg::RESULT_INTERRUPT_STATUS) & 0x07) == 0) {
        if (++count > 100000) return false;
    }

    writeReg(Reg::SYSTEM_INTERRUPT_CLEAR, 0x01);
    writeReg(Reg::SYSRANGE_START, 0x00);

    // Restore sequence config
    writeReg(Reg::SYSTEM_SEQUENCE_CONFIG, 0xE8);

    return true;
}

// ============================================================================
// Measurement control
// ============================================================================

bool Vl53l0x::startContinuous() {
    writeReg(0x80, 0x01);
    writeReg(0xFF, 0x01);
    writeReg(0x00, 0x00);
    writeReg(0x91, stopVariable_);
    writeReg(0x00, 0x01);
    writeReg(0xFF, 0x00);
    writeReg(0x80, 0x00);

    // Start continuous back-to-back mode
    writeReg(Reg::SYSRANGE_START, 0x02);

    return true;
}

void Vl53l0x::stopContinuous() {
    writeReg(Reg::SYSRANGE_START, 0x01);

    writeReg(0xFF, 0x01);
    writeReg(0x00, 0x00);
    writeReg(0x91, 0x00);
    writeReg(0x00, 0x01);
    writeReg(0xFF, 0x00);
}

uint16_t Vl53l0x::readRangeContinuousMillimeters() {
    timeout_ = false;
    uint32_t count = 0;
    uint32_t maxCount = (uint32_t)timeoutMs_ * 100;

    while ((readReg(Reg::RESULT_INTERRUPT_STATUS) & 0x07) == 0) {
        if (++count > maxCount) {
            timeout_ = true;
            return 0xFFFF;
        }
    }

    // Read range
    uint16_t range = readReg16(Reg::RESULT_RANGE_STATUS + 10);

    // Clear interrupt
    writeReg(Reg::SYSTEM_INTERRUPT_CLEAR, 0x01);

    return range;
}

uint16_t Vl53l0x::readRangeSingleMillimeters() {
    writeReg(0x80, 0x01);
    writeReg(0xFF, 0x01);
    writeReg(0x00, 0x00);
    writeReg(0x91, stopVariable_);
    writeReg(0x00, 0x01);
    writeReg(0xFF, 0x00);
    writeReg(0x80, 0x00);

    writeReg(Reg::SYSRANGE_START, 0x01);

    // Wait for start bit to clear
    uint32_t count = 0;
    while (readReg(Reg::SYSRANGE_START) & 0x01) {
        if (++count > 100000) {
            timeout_ = true;
            return 0xFFFF;
        }
    }

    return readRangeContinuousMillimeters();
}

bool Vl53l0x::setMeasurementTimingBudget(TimingBudget budget) {
    return setMeasurementTimingBudget(static_cast<uint32_t>(budget));
}

bool Vl53l0x::setMeasurementTimingBudget(uint32_t budgetUs) {
    if (budgetUs < 20000) return false;

    measurementTimingBudgetUs_ = budgetUs;

    // Simplified timing budget setting
    // For full implementation, need to adjust VCSEL periods and timeouts

    uint32_t finalRangeTimeoutUs = budgetUs - 4300; // Overhead
    uint16_t finalRangeTimeoutMclks = (uint16_t)timeoutMicrosecondsToMclks(finalRangeTimeoutUs, 14);
    uint16_t encoded = encodeTimeout(finalRangeTimeoutMclks);

    writeReg16(Reg::FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI, encoded);

    return true;
}

} // namespace hal
