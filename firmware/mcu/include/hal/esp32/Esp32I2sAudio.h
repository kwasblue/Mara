#pragma once

#include "../II2sAudio.h"
#include <driver/i2s.h>

namespace hal {

/// ESP32 I2S audio implementation using ESP-IDF I2S driver
class Esp32I2sAudio : public II2sAudio {
public:
    /// Construct with I2S port number
    /// @param port I2S port (0 or 1 on ESP32)
    explicit Esp32I2sAudio(i2s_port_t port = I2S_NUM_0);
    ~Esp32I2sAudio();

    I2sResult beginRx(const I2sConfig& config, const I2sPins& pins) override;
    I2sResult read(void* buffer, size_t bufferSize,
                   size_t* bytesRead, uint32_t timeoutMs) override;
    void end() override;
    bool isRunning() const override;

private:
    i2s_port_t port_;
    bool running_ = false;

    /// Convert HAL bits per sample to ESP-IDF enum
    static i2s_bits_per_sample_t toEspBits(I2sBitsPerSample bits);

    /// Convert HAL channel format to ESP-IDF enum
    static i2s_channel_fmt_t toEspChannelFormat(I2sChannelFormat fmt);
};

} // namespace hal
