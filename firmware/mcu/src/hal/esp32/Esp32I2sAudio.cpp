#include "hal/esp32/Esp32I2sAudio.h"
#include <Arduino.h>

namespace hal {

Esp32I2sAudio::Esp32I2sAudio(i2s_port_t port) : port_(port) {}

Esp32I2sAudio::~Esp32I2sAudio() {
    if (running_) {
        end();
    }
}

i2s_bits_per_sample_t Esp32I2sAudio::toEspBits(I2sBitsPerSample bits) {
    switch (bits) {
        case I2sBitsPerSample::Bits16:
            return I2S_BITS_PER_SAMPLE_16BIT;
        case I2sBitsPerSample::Bits24:
            return I2S_BITS_PER_SAMPLE_24BIT;
        case I2sBitsPerSample::Bits32:
        default:
            return I2S_BITS_PER_SAMPLE_32BIT;
    }
}

i2s_channel_fmt_t Esp32I2sAudio::toEspChannelFormat(I2sChannelFormat fmt) {
    switch (fmt) {
        case I2sChannelFormat::RightOnly:
            return I2S_CHANNEL_FMT_ONLY_RIGHT;
        case I2sChannelFormat::Stereo:
            return I2S_CHANNEL_FMT_RIGHT_LEFT;
        case I2sChannelFormat::LeftOnly:
        default:
            return I2S_CHANNEL_FMT_ONLY_LEFT;
    }
}

I2sResult Esp32I2sAudio::beginRx(const I2sConfig& config, const I2sPins& pins) {
    if (running_) {
        end();
    }

    i2s_config_t i2sCfg = {};
    i2sCfg.mode = static_cast<i2s_mode_t>(I2S_MODE_MASTER | I2S_MODE_RX);
    i2sCfg.sample_rate = config.sample_rate;
    i2sCfg.bits_per_sample = toEspBits(config.bits);
    i2sCfg.channel_format = toEspChannelFormat(config.channel);
    i2sCfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    i2sCfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    i2sCfg.dma_buf_count = config.dma_buf_count;
    i2sCfg.dma_buf_len = config.dma_buf_len;
    i2sCfg.use_apll = false;
    i2sCfg.tx_desc_auto_clear = false;
    i2sCfg.fixed_mclk = 0;

    esp_err_t err = i2s_driver_install(port_, &i2sCfg, 0, nullptr);
    if (err != ESP_OK) {
        Serial.printf("[Esp32I2sAudio] i2s_driver_install failed: %d\n", err);
        return I2sResult::ErrorDriver;
    }

    i2s_pin_config_t pinCfg = {};
    pinCfg.bck_io_num = pins.bck_pin;
    pinCfg.ws_io_num = pins.ws_pin;
    pinCfg.data_out_num = pins.data_out_pin >= 0 ? pins.data_out_pin : I2S_PIN_NO_CHANGE;
    pinCfg.data_in_num = pins.data_in_pin >= 0 ? pins.data_in_pin : I2S_PIN_NO_CHANGE;

    err = i2s_set_pin(port_, &pinCfg);
    if (err != ESP_OK) {
        Serial.printf("[Esp32I2sAudio] i2s_set_pin failed: %d\n", err);
        i2s_driver_uninstall(port_);
        return I2sResult::ErrorPins;
    }

    // Clear buffer with a dummy read
    size_t bytesRead = 0;
    uint8_t dummy[256];
    i2s_read(port_, dummy, sizeof(dummy), &bytesRead, 10);

    running_ = true;
    return I2sResult::Ok;
}

I2sResult Esp32I2sAudio::read(void* buffer, size_t bufferSize,
                              size_t* bytesRead, uint32_t timeoutMs) {
    if (!running_) {
        return I2sResult::ErrorNotStarted;
    }

    if (buffer == nullptr || bytesRead == nullptr) {
        return I2sResult::ErrorInvalidParam;
    }

    TickType_t ticks = pdMS_TO_TICKS(timeoutMs);
    esp_err_t err = i2s_read(port_, buffer, bufferSize, bytesRead, ticks);

    if (err != ESP_OK) {
        return I2sResult::ErrorTimeout;
    }

    return I2sResult::Ok;
}

void Esp32I2sAudio::end() {
    if (running_) {
        i2s_driver_uninstall(port_);
        running_ = false;
    }
}

bool Esp32I2sAudio::isRunning() const {
    return running_;
}

} // namespace hal
