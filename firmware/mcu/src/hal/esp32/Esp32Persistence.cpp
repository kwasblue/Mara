#include "hal/esp32/Esp32Persistence.h"

namespace hal {

Esp32Persistence::~Esp32Persistence() {
    if (opened_) {
        end();
    }
}

bool Esp32Persistence::begin(const char* ns, bool readOnly) {
    if (opened_) {
        end();
    }
    opened_ = prefs_.begin(ns, readOnly);
    return opened_;
}

void Esp32Persistence::end() {
    if (opened_) {
        prefs_.end();
        opened_ = false;
    }
}

uint8_t Esp32Persistence::getUChar(const char* key, uint8_t defaultValue) {
    return prefs_.getUChar(key, defaultValue);
}

bool Esp32Persistence::putUChar(const char* key, uint8_t value) {
    return prefs_.putUChar(key, value) > 0;
}

uint32_t Esp32Persistence::getUInt(const char* key, uint32_t defaultValue) {
    return prefs_.getUInt(key, defaultValue);
}

bool Esp32Persistence::putUInt(const char* key, uint32_t value) {
    return prefs_.putUInt(key, value) > 0;
}

int32_t Esp32Persistence::getInt(const char* key, int32_t defaultValue) {
    return prefs_.getInt(key, defaultValue);
}

bool Esp32Persistence::putInt(const char* key, int32_t value) {
    return prefs_.putInt(key, value) > 0;
}

float Esp32Persistence::getFloat(const char* key, float defaultValue) {
    return prefs_.getFloat(key, defaultValue);
}

bool Esp32Persistence::putFloat(const char* key, float value) {
    return prefs_.putFloat(key, value) > 0;
}

bool Esp32Persistence::getBool(const char* key, bool defaultValue) {
    return prefs_.getBool(key, defaultValue);
}

bool Esp32Persistence::putBool(const char* key, bool value) {
    return prefs_.putBool(key, value) > 0;
}

size_t Esp32Persistence::getString(const char* key, char* buffer, size_t maxLen) {
    // NOTE: If stored string is longer than maxLen, it will be silently truncated.
    // The ESP32 Preferences API does not provide a way to query the stored length
    // before reading. Callers should use sufficiently large buffers for expected data.
    return prefs_.getString(key, buffer, maxLen);
}

bool Esp32Persistence::putString(const char* key, const char* value) {
    return prefs_.putString(key, value) > 0;
}

bool Esp32Persistence::isKey(const char* key) {
    return prefs_.isKey(key);
}

bool Esp32Persistence::remove(const char* key) {
    return prefs_.remove(key);
}

bool Esp32Persistence::clear() {
    return prefs_.clear();
}

} // namespace hal
