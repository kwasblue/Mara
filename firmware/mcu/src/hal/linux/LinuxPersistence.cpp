// src/hal/linux/LinuxPersistence.cpp
// Linux persistence using file-based JSON storage

#include "hal/linux/LinuxPersistence.h"

#if PLATFORM_LINUX

#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <sys/stat.h>
#include <unistd.h>
#include <pwd.h>

namespace hal {

LinuxPersistence::LinuxPersistence(const char* basePath) {
    if (basePath && basePath[0] != '\0') {
        basePath_ = basePath;
    } else {
        // Default to ~/.mara
        const char* home = getenv("HOME");
        if (!home) {
            struct passwd* pw = getpwuid(getuid());
            if (pw) {
                home = pw->pw_dir;
            }
        }
        if (home) {
            basePath_ = std::string(home) + "/.mara";
        } else {
            basePath_ = "/tmp/.mara";
        }
    }
}

LinuxPersistence::~LinuxPersistence() {
    end();
}

bool LinuxPersistence::begin(const char* ns, bool readOnly) {
    if (isOpen_) {
        end();
    }

    currentNamespace_ = ns ? ns : "config";
    currentFilePath_ = buildFilePath(currentNamespace_.c_str());
    readOnly_ = readOnly;
    dirty_ = false;
    data_.clear();

    if (!ensureDirectory()) {
        return false;
    }

    loadFromFile();  // OK if file doesn't exist yet
    isOpen_ = true;
    return true;
}

void LinuxPersistence::end() {
    if (!isOpen_) return;

    if (dirty_ && !readOnly_) {
        saveToFile();
    }

    data_.clear();
    isOpen_ = false;
    dirty_ = false;
}

uint8_t LinuxPersistence::getUChar(const char* key, uint8_t defaultValue) {
    auto it = data_.find(key);
    if (it == data_.end()) return defaultValue;
    if (it->second.type == ValueType::UInt) {
        return static_cast<uint8_t>(it->second.uintVal);
    }
    return defaultValue;
}

bool LinuxPersistence::putUChar(const char* key, uint8_t value) {
    if (readOnly_) return false;
    JsonValue jv;
    jv.type = ValueType::UInt;
    jv.uintVal = value;
    data_[key] = jv;
    dirty_ = true;
    return true;
}

uint32_t LinuxPersistence::getUInt(const char* key, uint32_t defaultValue) {
    auto it = data_.find(key);
    if (it == data_.end()) return defaultValue;
    if (it->second.type == ValueType::UInt) {
        return it->second.uintVal;
    }
    return defaultValue;
}

bool LinuxPersistence::putUInt(const char* key, uint32_t value) {
    if (readOnly_) return false;
    JsonValue jv;
    jv.type = ValueType::UInt;
    jv.uintVal = value;
    data_[key] = jv;
    dirty_ = true;
    return true;
}

int32_t LinuxPersistence::getInt(const char* key, int32_t defaultValue) {
    auto it = data_.find(key);
    if (it == data_.end()) return defaultValue;
    if (it->second.type == ValueType::Int) {
        return it->second.intVal;
    }
    return defaultValue;
}

bool LinuxPersistence::putInt(const char* key, int32_t value) {
    if (readOnly_) return false;
    JsonValue jv;
    jv.type = ValueType::Int;
    jv.intVal = value;
    data_[key] = jv;
    dirty_ = true;
    return true;
}

float LinuxPersistence::getFloat(const char* key, float defaultValue) {
    auto it = data_.find(key);
    if (it == data_.end()) return defaultValue;
    if (it->second.type == ValueType::Float) {
        return it->second.floatVal;
    }
    return defaultValue;
}

bool LinuxPersistence::putFloat(const char* key, float value) {
    if (readOnly_) return false;
    JsonValue jv;
    jv.type = ValueType::Float;
    jv.floatVal = value;
    data_[key] = jv;
    dirty_ = true;
    return true;
}

bool LinuxPersistence::getBool(const char* key, bool defaultValue) {
    auto it = data_.find(key);
    if (it == data_.end()) return defaultValue;
    if (it->second.type == ValueType::Bool) {
        return it->second.boolVal;
    }
    return defaultValue;
}

bool LinuxPersistence::putBool(const char* key, bool value) {
    if (readOnly_) return false;
    JsonValue jv;
    jv.type = ValueType::Bool;
    jv.boolVal = value;
    data_[key] = jv;
    dirty_ = true;
    return true;
}

size_t LinuxPersistence::getString(const char* key, char* buffer, size_t maxLen) {
    auto it = data_.find(key);
    if (it == data_.end() || it->second.type != ValueType::String) {
        if (maxLen > 0) buffer[0] = '\0';
        return 0;
    }

    size_t len = it->second.strVal.size();
    size_t copyLen = (len < maxLen - 1) ? len : maxLen - 1;
    memcpy(buffer, it->second.strVal.c_str(), copyLen);
    buffer[copyLen] = '\0';
    return len;
}

bool LinuxPersistence::putString(const char* key, const char* value) {
    if (readOnly_) return false;
    JsonValue jv;
    jv.type = ValueType::String;
    jv.strVal = value;
    data_[key] = jv;
    dirty_ = true;
    return true;
}

size_t LinuxPersistence::getBytesLength(const char* key) {
    auto it = data_.find(key);
    if (it == data_.end() || it->second.type != ValueType::Bytes) {
        return 0;
    }
    return decodeBase64(it->second.bytesBase64).size();
}

size_t LinuxPersistence::getBytes(const char* key, void* buffer, size_t maxLen) {
    auto it = data_.find(key);
    if (it == data_.end() || it->second.type != ValueType::Bytes) {
        return 0;
    }

    std::vector<uint8_t> decoded = decodeBase64(it->second.bytesBase64);
    size_t copyLen = (decoded.size() < maxLen) ? decoded.size() : maxLen;
    memcpy(buffer, decoded.data(), copyLen);
    return decoded.size();
}

size_t LinuxPersistence::putBytes(const char* key, const void* data, size_t len) {
    if (readOnly_) return 0;
    JsonValue jv;
    jv.type = ValueType::Bytes;
    jv.bytesBase64 = encodeBase64(data, len);
    data_[key] = jv;
    dirty_ = true;
    return len;
}

bool LinuxPersistence::isKey(const char* key) {
    return data_.find(key) != data_.end();
}

bool LinuxPersistence::remove(const char* key) {
    if (readOnly_) return false;
    auto it = data_.find(key);
    if (it == data_.end()) return false;
    data_.erase(it);
    dirty_ = true;
    return true;
}

bool LinuxPersistence::clear() {
    if (readOnly_) return false;
    data_.clear();
    dirty_ = true;
    return true;
}

void LinuxPersistence::setBasePath(const char* path) {
    basePath_ = path;
}

const char* LinuxPersistence::getBasePath() const {
    return basePath_.c_str();
}

bool LinuxPersistence::ensureDirectory() {
    struct stat st;
    if (stat(basePath_.c_str(), &st) == 0) {
        return S_ISDIR(st.st_mode);
    }
    return mkdir(basePath_.c_str(), 0755) == 0;
}

std::string LinuxPersistence::buildFilePath(const char* ns) {
    return basePath_ + "/" + ns + ".json";
}

bool LinuxPersistence::loadFromFile() {
    std::ifstream file(currentFilePath_);
    if (!file.is_open()) {
        return false;  // File doesn't exist yet
    }

    std::stringstream buffer;
    buffer << file.rdbuf();
    parseJsonFile(buffer.str());
    return true;
}

bool LinuxPersistence::saveToFile() {
    std::ofstream file(currentFilePath_);
    if (!file.is_open()) {
        return false;
    }

    file << serializeToJson();
    return true;
}

// Simple JSON parser (handles flat object with primitive values)
void LinuxPersistence::parseJsonFile(const std::string& content) {
    data_.clear();

    // Very simple JSON parser for {"key": value, ...} format
    size_t pos = content.find('{');
    if (pos == std::string::npos) return;
    pos++;

    while (pos < content.size()) {
        // Skip whitespace
        while (pos < content.size() && isspace(content[pos])) pos++;
        if (pos >= content.size() || content[pos] == '}') break;

        // Find key
        if (content[pos] != '"') break;
        size_t keyStart = ++pos;
        while (pos < content.size() && content[pos] != '"') pos++;
        std::string key = content.substr(keyStart, pos - keyStart);
        pos++;  // Skip closing quote

        // Skip colon
        while (pos < content.size() && (isspace(content[pos]) || content[pos] == ':')) pos++;

        // Parse value
        JsonValue jv;
        if (content[pos] == '"') {
            // String
            pos++;
            size_t valStart = pos;
            while (pos < content.size() && content[pos] != '"') pos++;
            jv.type = ValueType::String;
            jv.strVal = content.substr(valStart, pos - valStart);
            pos++;
        } else if (content[pos] == 't' || content[pos] == 'f') {
            // Boolean
            jv.type = ValueType::Bool;
            jv.boolVal = (content[pos] == 't');
            while (pos < content.size() && isalpha(content[pos])) pos++;
        } else if (content[pos] == 'n') {
            // null
            jv.type = ValueType::Null;
            while (pos < content.size() && isalpha(content[pos])) pos++;
        } else if (content[pos] == '-' || isdigit(content[pos])) {
            // Number
            size_t numStart = pos;
            bool isFloat = false;
            bool isNeg = false;
            if (content[pos] == '-') { isNeg = true; pos++; }
            while (pos < content.size() && (isdigit(content[pos]) || content[pos] == '.')) {
                if (content[pos] == '.') isFloat = true;
                pos++;
            }
            std::string numStr = content.substr(numStart, pos - numStart);
            if (isFloat) {
                jv.type = ValueType::Float;
                jv.floatVal = std::stof(numStr);
            } else if (isNeg) {
                jv.type = ValueType::Int;
                jv.intVal = std::stoi(numStr);
            } else {
                jv.type = ValueType::UInt;
                jv.uintVal = std::stoul(numStr);
            }
        }

        data_[key] = jv;

        // Skip comma
        while (pos < content.size() && (isspace(content[pos]) || content[pos] == ',')) pos++;
    }
}

std::string LinuxPersistence::serializeToJson() {
    std::ostringstream out;
    out << "{\n";

    bool first = true;
    for (const auto& [key, val] : data_) {
        if (!first) out << ",\n";
        first = false;

        out << "  \"" << key << "\": ";
        switch (val.type) {
            case ValueType::Null:
                out << "null";
                break;
            case ValueType::Bool:
                out << (val.boolVal ? "true" : "false");
                break;
            case ValueType::Int:
                out << val.intVal;
                break;
            case ValueType::UInt:
                out << val.uintVal;
                break;
            case ValueType::Float:
                out << val.floatVal;
                break;
            case ValueType::String:
                out << "\"" << val.strVal << "\"";
                break;
            case ValueType::Bytes:
                out << "\"" << val.bytesBase64 << "\"";
                break;
        }
    }

    out << "\n}\n";
    return out.str();
}

std::string LinuxPersistence::encodeBase64(const void* data, size_t len) {
    static const char* chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    const uint8_t* bytes = static_cast<const uint8_t*>(data);
    std::string result;
    result.reserve(((len + 2) / 3) * 4);

    for (size_t i = 0; i < len; i += 3) {
        uint32_t n = static_cast<uint32_t>(bytes[i]) << 16;
        if (i + 1 < len) n |= static_cast<uint32_t>(bytes[i + 1]) << 8;
        if (i + 2 < len) n |= bytes[i + 2];

        result += chars[(n >> 18) & 0x3F];
        result += chars[(n >> 12) & 0x3F];
        result += (i + 1 < len) ? chars[(n >> 6) & 0x3F] : '=';
        result += (i + 2 < len) ? chars[n & 0x3F] : '=';
    }

    return result;
}

std::vector<uint8_t> LinuxPersistence::decodeBase64(const std::string& encoded) {
    static const int lookup[256] = {
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,62,-1,-1,-1,63,
        52,53,54,55,56,57,58,59,60,61,-1,-1,-1,-1,-1,-1,
        -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,
        15,16,17,18,19,20,21,22,23,24,25,-1,-1,-1,-1,-1,
        -1,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,
        41,42,43,44,45,46,47,48,49,50,51,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1
    };

    std::vector<uint8_t> result;
    result.reserve(encoded.size() * 3 / 4);

    uint32_t val = 0;
    int bits = 0;

    for (char c : encoded) {
        if (c == '=') break;
        int v = lookup[static_cast<unsigned char>(c)];
        if (v < 0) continue;

        val = (val << 6) | v;
        bits += 6;

        if (bits >= 8) {
            bits -= 8;
            result.push_back(static_cast<uint8_t>((val >> bits) & 0xFF));
        }
    }

    return result;
}

} // namespace hal

#endif // PLATFORM_LINUX
