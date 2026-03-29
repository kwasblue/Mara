#pragma once

#include <cstdint>
#include <cstddef>

namespace hal {

/// I2S channel format
enum class I2sChannelFormat : uint8_t {
    LeftOnly,       // Mono, left channel
    RightOnly,      // Mono, right channel
    Stereo          // Stereo (both channels)
};

/// I2S bits per sample
enum class I2sBitsPerSample : uint8_t {
    Bits16 = 16,
    Bits24 = 24,
    Bits32 = 32
};

/// I2S configuration
struct I2sConfig {
    uint32_t sample_rate = 16000;   // Sample rate in Hz
    I2sBitsPerSample bits = I2sBitsPerSample::Bits32;
    I2sChannelFormat channel = I2sChannelFormat::LeftOnly;
    uint8_t dma_buf_count = 4;      // Number of DMA buffers
    uint16_t dma_buf_len = 256;     // Length of each DMA buffer in samples
};

/// I2S pin configuration
struct I2sPins {
    int8_t bck_pin = -1;    // Bit clock (SCK/BCLK)
    int8_t ws_pin = -1;     // Word select (LRCLK/WS)
    int8_t data_in_pin = -1;  // Data input (SD for RX)
    int8_t data_out_pin = -1; // Data output (SD for TX)
};

/// Result codes for I2S operations
enum class I2sResult : uint8_t {
    Ok = 0,
    ErrorDriver,        // Driver installation failed
    ErrorPins,          // Pin configuration failed
    ErrorTimeout,       // Read/write timeout
    ErrorNotStarted,    // Driver not started
    ErrorInvalidParam   // Invalid parameter
};

/// Abstract I2S audio interface for platform portability
/// Provides I2S audio driver for microphone input.
///
/// Usage:
///   II2sAudio* audio = hal.i2sAudio;
///   I2sConfig cfg;
///   cfg.sample_rate = 16000;
///   I2sPins pins = { .bck_pin = 26, .ws_pin = 22, .data_in_pin = 21 };
///
///   if (audio->beginRx(cfg, pins) == I2sResult::Ok) {
///       int32_t buffer[256];
///       size_t bytesRead;
///       audio->read(buffer, sizeof(buffer), &bytesRead, 50);
///   }
///   audio->end();
///
/// Note: This interface is optional (nullptr if HAS_AUDIO is not defined).
class II2sAudio {
public:
    virtual ~II2sAudio() = default;

    /// Start I2S driver in receive (RX) mode for microphone input
    /// @param config I2S configuration
    /// @param pins Pin configuration
    /// @return Result code
    virtual I2sResult beginRx(const I2sConfig& config, const I2sPins& pins) = 0;

    /// Read audio data from I2S
    /// @param buffer Destination buffer
    /// @param bufferSize Size of buffer in bytes
    /// @param bytesRead Output: actual bytes read
    /// @param timeoutMs Timeout in milliseconds
    /// @return Result code
    virtual I2sResult read(void* buffer, size_t bufferSize,
                           size_t* bytesRead, uint32_t timeoutMs) = 0;

    /// Stop I2S driver and release resources
    virtual void end() = 0;

    /// Check if I2S driver is running
    virtual bool isRunning() const = 0;
};

} // namespace hal
