#pragma once

#include "../IPersistence.h"
#include <Preferences.h>

namespace hal {

/// ESP32 persistence implementation using Preferences (NVS)
class Esp32Persistence : public IPersistence {
public:
    Esp32Persistence() = default;
    ~Esp32Persistence();

    bool begin(const char* ns, bool readOnly) override;
    void end() override;

    uint8_t getUChar(const char* key, uint8_t defaultValue = 0) override;
    bool putUChar(const char* key, uint8_t value) override;

    uint32_t getUInt(const char* key, uint32_t defaultValue = 0) override;
    bool putUInt(const char* key, uint32_t value) override;

    int32_t getInt(const char* key, int32_t defaultValue = 0) override;
    bool putInt(const char* key, int32_t value) override;

    float getFloat(const char* key, float defaultValue = 0.0f) override;
    bool putFloat(const char* key, float value) override;

    bool getBool(const char* key, bool defaultValue = false) override;
    bool putBool(const char* key, bool value) override;

    size_t getString(const char* key, char* buffer, size_t maxLen) override;
    bool putString(const char* key, const char* value) override;

    size_t getBytesLength(const char* key) override;
    size_t getBytes(const char* key, void* buffer, size_t maxLen) override;
    size_t putBytes(const char* key, const void* data, size_t len) override;

    bool isKey(const char* key) override;
    bool remove(const char* key) override;
    bool clear() override;

private:
    Preferences prefs_;
    bool opened_ = false;
};

} // namespace hal
