// include/hal/stubs/StubPwm.h
#pragma once
#include "../IPwm.h"

namespace hal {

class StubPwm : public IPwm {
public:
    bool     attach(uint8_t channel, uint8_t pin, uint32_t frequency, uint8_t resolution = 12) override {
        (void)channel; (void)pin; (void)frequency; (void)resolution; return true;
    }
    void     detach(uint8_t channel) override { (void)channel; }
    void     setDuty(uint8_t channel, float duty) override { (void)channel; (void)duty; }
    void     setDutyRaw(uint8_t channel, uint32_t value) override { (void)channel; (void)value; }
    void     setFrequency(uint8_t channel, uint32_t frequency) override { (void)channel; (void)frequency; }
    uint32_t getFrequency(uint8_t channel) override { (void)channel; return 0; }
    uint8_t  getResolution(uint8_t channel) override { (void)channel; return 12; }
    uint8_t  maxChannels() const override { return 16; }
};

} // namespace hal
