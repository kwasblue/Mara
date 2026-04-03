// managers/MicManager.cpp
#include "sensor/MicManager.h"
#include <math.h>

bool MicManager::begin(gpio_num_t wsPin,
                       gpio_num_t sckPin,
                       gpio_num_t sdPin,
                       i2s_port_t port) {
    port_   = port;
    online_ = false;
    usingHal_ = false;

    i2s_config_t config = {};
    config.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
    config.sample_rate = 16000;  // 16 kHz is plenty for "robot noises"
    config.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
    config.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;  // using one channel
    config.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    config.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    config.dma_buf_count = 4;
    config.dma_buf_len = 256;
    config.use_apll = false;
    config.tx_desc_auto_clear = false;
    config.fixed_mclk = 0;

    esp_err_t err = i2s_driver_install(port_, &config, 0, nullptr);
    if (err != ESP_OK) {
        Serial.printf("[MicManager] i2s_driver_install failed: %d\n", err);
        return false;
    }

    i2s_pin_config_t pins = {};
    pins.bck_io_num   = sckPin;              // SCK / BCLK
    pins.ws_io_num    = wsPin;               // LRCLK / WS
    pins.data_out_num = I2S_PIN_NO_CHANGE;
    pins.data_in_num  = sdPin;               // SD

    err = i2s_set_pin(port_, &pins);
    if (err != ESP_OK) {
        Serial.printf("[MicManager] i2s_set_pin failed: %d\n", err);
        i2s_driver_uninstall(port_);
        return false;
    }

    // Optional: clear buffer with a dummy read
    size_t bytesRead = 0;
    uint8_t dummy[256];
    i2s_read(port_, dummy, sizeof(dummy), &bytesRead, 10);

    online_ = true;
    Serial.println("[MicManager] init OK");
    return true;
}

bool MicManager::beginHal(int8_t wsPin, int8_t sckPin, int8_t sdPin) {
    online_ = false;
    usingHal_ = false;

    if (!halAudio_) {
        Serial.println("[MicManager] HAL audio not set");
        return false;
    }

    hal::I2sConfig config;
    config.sample_rate = 16000;
    config.bits = hal::I2sBitsPerSample::Bits32;
    config.channel = hal::I2sChannelFormat::LeftOnly;
    config.dma_buf_count = 4;
    config.dma_buf_len = 256;

    hal::I2sPins pins;
    pins.bck_pin = sckPin;
    pins.ws_pin = wsPin;
    pins.data_in_pin = sdPin;
    pins.data_out_pin = -1;

    hal::I2sResult result = halAudio_->beginRx(config, pins);
    if (result != hal::I2sResult::Ok) {
        Serial.printf("[MicManager] HAL beginRx failed: %d\n", static_cast<int>(result));
        return false;
    }

    online_ = true;
    usingHal_ = true;
    Serial.println("[MicManager] HAL init OK");
    return true;
}

void MicManager::end() {
    if (!online_) {
        return;
    }

    if (usingHal_ && halAudio_) {
        halAudio_->end();
    } else {
        i2s_driver_uninstall(port_);
    }

    online_ = false;
    usingHal_ = false;
}

bool MicManager::readLevel(Level& outLevel, size_t sampleCount) {
    if (!online_) {
        return false;
    }

    // 32-bit samples
    const size_t bytesPerSample = sizeof(int32_t);

    // Clamp to buffer size
    if (sampleCount > kMaxSampleCount) {
        sampleCount = kMaxSampleCount;
    }
    const size_t bufBytes = sampleCount * bytesPerSample;

    size_t bytesRead = 0;

    if (usingHal_ && halAudio_) {
        // Use HAL interface
        hal::I2sResult result = halAudio_->read(sampleBuffer_, bufBytes, &bytesRead, 50);
        if (result != hal::I2sResult::Ok || bytesRead == 0) {
            return false;
        }
    } else {
        // Use direct ESP32 I2S driver
        esp_err_t err = i2s_read(
            port_,
            (void*)sampleBuffer_,
            bufBytes,
            &bytesRead,
            /*ticks_to_wait=*/50 / portTICK_PERIOD_MS
        );
        if (err != ESP_OK || bytesRead == 0) {
            // No data yet, or error
            return false;
        }
    }

    size_t actualSamples = bytesRead / bytesPerSample;
    if (actualSamples == 0) {
        return false;
    }

    double sumSq = 0.0;
    double peak  = 0.0;

    // INMP441 data is usually MSB-aligned 24-bit in a 32-bit word.
    // For simplicity, treat as full-scale 32-bit signed.
    const double denom = 2147483648.0;  // 2^31

    for (size_t i = 0; i < actualSamples; ++i) {
        int32_t raw = sampleBuffer_[i];

        double x = (double)raw / denom;   // normalize to -1..+1
        double a = fabs(x);

        sumSq += x * x;
        if (a > peak) peak = a;
    }

    double rms = sqrt(sumSq / (double)actualSamples);

    outLevel.rms  = (float)rms;
    outLevel.peak = (float)peak;
    outLevel.dbfs = (rms > 0.0)
        ? (float)(20.0 * log10(rms))
        : -120.0f;

    return true;
}
