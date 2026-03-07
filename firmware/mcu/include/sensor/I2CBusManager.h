// core/I2CBusManager.h
#pragma once
#include <Wire.h>
#include <map>
#include <string>

class I2CBusManager {
public:
    bool begin(int sda_pin, int scl_pin, uint32_t freq_hz = 400000) {
        Wire.begin(sda_pin, scl_pin, freq_hz);
        // Optional: quick scan, log what we see
        return true;
    }

    bool registerDevice(const std::string& name, uint8_t address) {
        devices_[name] = address;
        return true;
    }

    uint8_t addr(const std::string& name) const {
        auto it = devices_.find(name);
        return (it != devices_.end()) ? it->second : 0xFF;
    }

    TwoWire& bus() { return Wire; }

private:
    std::map<std::string, uint8_t> devices_;
};
