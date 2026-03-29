#pragma once

#include <cstdint>
#include <cstddef>

namespace hal {

/// Abstract persistence interface for platform portability
/// Provides key-value NVS (Non-Volatile Storage) for configuration and diagnostics.
///
/// Usage:
///   IPersistence* persist = hal.persistence;
///
///   if (persist->begin("my_namespace", true)) {  // read-only
///       uint32_t count = persist->getUInt("boot_cnt", 0);
///       persist->end();
///   }
///
///   if (persist->begin("my_namespace", false)) { // read-write
///       persist->putUInt("boot_cnt", count + 1);
///       persist->end();
///   }
///
/// Notes:
///   - Namespace names should be <= 15 characters
///   - Key names should be <= 15 characters
///   - Always call end() after operations are complete
///   - String values have platform-specific max length (typically 4000 bytes)
class IPersistence {
public:
    virtual ~IPersistence() = default;

    /// Open a namespace for read or write operations
    /// @param ns Namespace name (max 15 chars)
    /// @param readOnly If true, open read-only; if false, allow writes
    /// @return true if namespace opened successfully
    virtual bool begin(const char* ns, bool readOnly) = 0;

    /// Close the currently open namespace
    virtual void end() = 0;

    // =========================================================================
    // Unsigned integer operations
    // =========================================================================

    /// Get unsigned 8-bit integer
    virtual uint8_t getUChar(const char* key, uint8_t defaultValue = 0) = 0;

    /// Put unsigned 8-bit integer
    virtual bool putUChar(const char* key, uint8_t value) = 0;

    /// Get unsigned 32-bit integer
    virtual uint32_t getUInt(const char* key, uint32_t defaultValue = 0) = 0;

    /// Put unsigned 32-bit integer
    virtual bool putUInt(const char* key, uint32_t value) = 0;

    // =========================================================================
    // Signed integer operations
    // =========================================================================

    /// Get signed 32-bit integer
    virtual int32_t getInt(const char* key, int32_t defaultValue = 0) = 0;

    /// Put signed 32-bit integer
    virtual bool putInt(const char* key, int32_t value) = 0;

    // =========================================================================
    // Floating point operations
    // =========================================================================

    /// Get 32-bit float
    virtual float getFloat(const char* key, float defaultValue = 0.0f) = 0;

    /// Put 32-bit float
    virtual bool putFloat(const char* key, float value) = 0;

    // =========================================================================
    // Boolean operations
    // =========================================================================

    /// Get boolean
    virtual bool getBool(const char* key, bool defaultValue = false) = 0;

    /// Put boolean
    virtual bool putBool(const char* key, bool value) = 0;

    // =========================================================================
    // String operations
    // =========================================================================

    /// Get string into buffer
    /// @param key Key name
    /// @param buffer Destination buffer
    /// @param maxLen Maximum buffer length
    /// @return Number of characters read (excluding null terminator), 0 if not found
    virtual size_t getString(const char* key, char* buffer, size_t maxLen) = 0;

    /// Put string
    virtual bool putString(const char* key, const char* value) = 0;

    // =========================================================================
    // Utility operations
    // =========================================================================

    /// Check if a key exists in the current namespace
    virtual bool isKey(const char* key) = 0;

    /// Remove a key from the current namespace
    virtual bool remove(const char* key) = 0;

    /// Clear all keys in the current namespace
    virtual bool clear() = 0;
};

} // namespace hal
