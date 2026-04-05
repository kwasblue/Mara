// include/hal/linux/LinuxPersistence.h
// Linux persistence implementation using file-based JSON storage
//
// Stores configuration in ~/.mara/ directory structure.
#pragma once

#include "../IPersistence.h"
#include <cstdint>
#include <cstring>
#include <string>
#include <map>

namespace hal {

/// Linux persistence using JSON files
///
/// Stores key-value pairs in ~/.mara/<namespace>.json files.
/// Compatible with IPersistence interface used on ESP32 (NVS).
///
/// Directory structure:
///   ~/.mara/
///     config.json     (default namespace)
///     sensors.json    (sensor calibration)
///     identity.json   (device identity)
///
/// Note: Creates ~/.mara/ directory if it doesn't exist.
class LinuxPersistence : public IPersistence {
public:
    /// Constructor
    /// @param basePath Base directory for storage (default: ~/.mara)
    explicit LinuxPersistence(const char* basePath = nullptr);

    ~LinuxPersistence();

    bool begin(const char* ns, bool readOnly) override;
    void end() override;

    // Unsigned integers
    uint8_t getUChar(const char* key, uint8_t defaultValue = 0) override;
    bool putUChar(const char* key, uint8_t value) override;
    uint32_t getUInt(const char* key, uint32_t defaultValue = 0) override;
    bool putUInt(const char* key, uint32_t value) override;

    // Signed integers
    int32_t getInt(const char* key, int32_t defaultValue = 0) override;
    bool putInt(const char* key, int32_t value) override;

    // Floats
    float getFloat(const char* key, float defaultValue = 0.0f) override;
    bool putFloat(const char* key, float value) override;

    // Booleans
    bool getBool(const char* key, bool defaultValue = false) override;
    bool putBool(const char* key, bool value) override;

    // Strings
    size_t getString(const char* key, char* buffer, size_t maxLen) override;
    bool putString(const char* key, const char* value) override;

    // Blobs
    size_t getBytesLength(const char* key) override;
    size_t getBytes(const char* key, void* buffer, size_t maxLen) override;
    size_t putBytes(const char* key, const void* data, size_t len) override;

    // Utilities
    bool isKey(const char* key) override;
    bool remove(const char* key) override;
    bool clear() override;

    /// Set custom base path
    void setBasePath(const char* path);

    /// Get current base path
    const char* getBasePath() const;

private:
    // JSON value types
    enum class ValueType {
        Null,
        Bool,
        Int,
        UInt,
        Float,
        String,
        Bytes
    };

    struct JsonValue {
        ValueType type = ValueType::Null;
        union {
            bool boolVal;
            int32_t intVal;
            uint32_t uintVal;
            float floatVal;
        };
        std::string strVal;
        std::string bytesBase64;
    };

    std::string basePath_;
    std::string currentNamespace_;
    std::string currentFilePath_;
    bool isOpen_ = false;
    bool readOnly_ = true;
    bool dirty_ = false;
    std::map<std::string, JsonValue> data_;

    bool ensureDirectory();
    bool loadFromFile();
    bool saveToFile();
    std::string buildFilePath(const char* ns);
    std::string encodeBase64(const void* data, size_t len);
    std::vector<uint8_t> decodeBase64(const std::string& encoded);
    void parseJsonFile(const std::string& content);
    std::string serializeToJson();
};

} // namespace hal
