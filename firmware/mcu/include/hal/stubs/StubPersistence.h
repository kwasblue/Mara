// include/hal/stubs/StubPersistence.h
// Stub persistence implementation for native/test builds
#pragma once

#include "../IPersistence.h"

namespace hal {

class StubPersistence : public IPersistence {
public:
    bool begin(const char* ns, bool readOnly) override {
        (void)ns; (void)readOnly;
        return true;
    }

    void end() override {}

    // Unsigned integers
    uint8_t getUChar(const char* key, uint8_t defaultValue = 0) override {
        (void)key;
        return defaultValue;
    }
    bool putUChar(const char* key, uint8_t value) override {
        (void)key; (void)value;
        return true;
    }
    uint32_t getUInt(const char* key, uint32_t defaultValue = 0) override {
        (void)key;
        return defaultValue;
    }
    bool putUInt(const char* key, uint32_t value) override {
        (void)key; (void)value;
        return true;
    }

    // Signed integers
    int32_t getInt(const char* key, int32_t defaultValue = 0) override {
        (void)key;
        return defaultValue;
    }
    bool putInt(const char* key, int32_t value) override {
        (void)key; (void)value;
        return true;
    }

    // Floats
    float getFloat(const char* key, float defaultValue = 0.0f) override {
        (void)key;
        return defaultValue;
    }
    bool putFloat(const char* key, float value) override {
        (void)key; (void)value;
        return true;
    }

    // Booleans
    bool getBool(const char* key, bool defaultValue = false) override {
        (void)key;
        return defaultValue;
    }
    bool putBool(const char* key, bool value) override {
        (void)key; (void)value;
        return true;
    }

    // Strings
    size_t getString(const char* key, char* buffer, size_t maxLen) override {
        (void)key; (void)buffer; (void)maxLen;
        return 0;
    }
    bool putString(const char* key, const char* value) override {
        (void)key; (void)value;
        return true;
    }

    // Utilities
    bool isKey(const char* key) override { (void)key; return false; }
    bool remove(const char* key) override { (void)key; return true; }
    bool clear() override { return true; }
};

} // namespace hal
