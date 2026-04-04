// include/hal/stubs/StubPwm.h
#pragma once
#include "../IPwm.h"

namespace hal {

class StubPwm : public IPwm {
public:
    bool attach(uint8_t channel, uint8_t pin, uint32_t freq, uint8_t resolution) override {
        (void)channel; (void)pin; (void)freq; (void)resolution; return true;
    }
    void detach(uint8_t channel) override { (void)channel; }
    void write(uint8_t channel, uint32_t duty) override { (void)channel; (void)duty; }
    void writeFloat(uint8_t channel, float duty) override { (void)channel; (void)duty; }
    uint32_t getMaxDuty(uint8_t channel) const override { (void)channel; return 255; }
};

} // namespace hal
