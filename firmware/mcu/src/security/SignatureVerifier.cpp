// src/security/SignatureVerifier.cpp
// HMAC-SHA256 signature verification implementation

#include "security/SignatureVerifier.h"
#include <string.h>

#if defined(ARDUINO_ARCH_ESP32)
#include "mbedtls/md.h"
#include "mbedtls/sha256.h"
#else
// Native build: use minimal SHA256 implementation for testing
#include <cstring>
#endif

namespace mara {

void SignatureVerifier::setKey(const uint8_t* key, size_t len) {
    if (key == nullptr || len == 0) {
        clearKey();
        return;
    }

    size_t copyLen = (len > KEY_SIZE) ? KEY_SIZE : len;
    memcpy(key_, key, copyLen);
    keyLen_ = copyLen;
    hasKey_ = true;

    // Zero-pad if key is shorter than KEY_SIZE
    if (copyLen < KEY_SIZE) {
        memset(key_ + copyLen, 0, KEY_SIZE - copyLen);
    }
}

void SignatureVerifier::clearKey() {
    memset(key_, 0, KEY_SIZE);
    keyLen_ = 0;
    hasKey_ = false;
}

bool SignatureVerifier::verify(const char* payload, size_t payloadLen, const char* signature) const {
    if (!hasKey_ || signature == nullptr) {
        return false;
    }

    // Signature should be 64 hex characters
    size_t sigLen = strlen(signature);
    if (sigLen != SIGNATURE_SIZE) {
        return false;
    }

    // Compute expected HMAC
    uint8_t computed[32];
    hmacSha256(key_, keyLen_,
               reinterpret_cast<const uint8_t*>(payload), payloadLen,
               computed);

    // Convert signature from hex
    uint8_t expected[32];
    if (!hexToBytes(signature, sigLen, expected, 32)) {
        return false;
    }

    // Constant-time comparison to prevent timing attacks
    uint8_t diff = 0;
    for (size_t i = 0; i < 32; ++i) {
        diff |= computed[i] ^ expected[i];
    }

    return diff == 0;
}

bool SignatureVerifier::sign(const char* payload, size_t payloadLen, char* outSignature) const {
    if (!hasKey_ || outSignature == nullptr) {
        return false;
    }

    uint8_t hmac[32];
    hmacSha256(key_, keyLen_,
               reinterpret_cast<const uint8_t*>(payload), payloadLen,
               hmac);

    bytesToHex(hmac, 32, outSignature);
    outSignature[64] = '\0';
    return true;
}

void SignatureVerifier::hmacSha256(const uint8_t* key, size_t keyLen,
                                   const uint8_t* data, size_t dataLen,
                                   uint8_t* out) const {
#if defined(ARDUINO_ARCH_ESP32)
    // Use mbedtls for ESP32
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);

    const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    mbedtls_md_setup(&ctx, info, 1);  // 1 = HMAC mode
    mbedtls_md_hmac_starts(&ctx, key, keyLen);
    mbedtls_md_hmac_update(&ctx, data, dataLen);
    mbedtls_md_hmac_finish(&ctx, out);
    mbedtls_md_free(&ctx);
#else
    // Minimal HMAC-SHA256 for native testing
    // HMAC(K, m) = H((K' ^ opad) || H((K' ^ ipad) || m))
    // Where K' is key padded to block size (64 bytes for SHA256)

    static constexpr size_t BLOCK_SIZE = 64;
    static constexpr size_t HASH_SIZE = 32;
    static constexpr uint8_t IPAD = 0x36;
    static constexpr uint8_t OPAD = 0x5C;

    uint8_t keyPadded[BLOCK_SIZE];
    memset(keyPadded, 0, BLOCK_SIZE);

    // If key > block size, hash it first
    if (keyLen > BLOCK_SIZE) {
        sha256(key, keyLen, keyPadded);
    } else {
        memcpy(keyPadded, key, keyLen);
    }

    // Inner hash: H((K' ^ ipad) || m)
    uint8_t innerPad[BLOCK_SIZE];
    for (size_t i = 0; i < BLOCK_SIZE; ++i) {
        innerPad[i] = keyPadded[i] ^ IPAD;
    }

    // Allocate buffer for inner pad + data
    uint8_t* innerData = new uint8_t[BLOCK_SIZE + dataLen];
    memcpy(innerData, innerPad, BLOCK_SIZE);
    memcpy(innerData + BLOCK_SIZE, data, dataLen);

    uint8_t innerHash[HASH_SIZE];
    sha256(innerData, BLOCK_SIZE + dataLen, innerHash);
    delete[] innerData;

    // Outer hash: H((K' ^ opad) || inner_hash)
    uint8_t outerPad[BLOCK_SIZE];
    for (size_t i = 0; i < BLOCK_SIZE; ++i) {
        outerPad[i] = keyPadded[i] ^ OPAD;
    }

    uint8_t outerData[BLOCK_SIZE + HASH_SIZE];
    memcpy(outerData, outerPad, BLOCK_SIZE);
    memcpy(outerData + BLOCK_SIZE, innerHash, HASH_SIZE);

    sha256(outerData, BLOCK_SIZE + HASH_SIZE, out);
#endif
}

void SignatureVerifier::sha256(const uint8_t* data, size_t len, uint8_t* out) const {
#if defined(ARDUINO_ARCH_ESP32)
    mbedtls_sha256(data, len, out, 0);  // 0 = SHA256 (not SHA224)
#else
    // Minimal SHA256 for native testing
    // This is a simplified implementation - in production, use a proper library

    // SHA256 constants
    static const uint32_t K[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    };

    auto rotr = [](uint32_t x, uint32_t n) -> uint32_t { return (x >> n) | (x << (32 - n)); };
    auto ch = [](uint32_t x, uint32_t y, uint32_t z) -> uint32_t { return (x & y) ^ (~x & z); };
    auto maj = [](uint32_t x, uint32_t y, uint32_t z) -> uint32_t { return (x & y) ^ (x & z) ^ (y & z); };
    auto sigma0 = [&rotr](uint32_t x) -> uint32_t { return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22); };
    auto sigma1 = [&rotr](uint32_t x) -> uint32_t { return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25); };
    auto gamma0 = [&rotr](uint32_t x) -> uint32_t { return rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3); };
    auto gamma1 = [&rotr](uint32_t x) -> uint32_t { return rotr(x, 17) ^ rotr(x, 19) ^ (x >> 10); };

    // Initial hash values
    uint32_t h[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };

    // Pre-processing: padding
    size_t origLen = len;
    size_t newLen = ((len + 8) / 64 + 1) * 64;
    uint8_t* msg = new uint8_t[newLen];
    memcpy(msg, data, len);
    msg[len] = 0x80;
    memset(msg + len + 1, 0, newLen - len - 1 - 8);

    // Append original length in bits as big-endian 64-bit
    uint64_t bitLen = origLen * 8;
    for (int i = 0; i < 8; ++i) {
        msg[newLen - 1 - i] = static_cast<uint8_t>(bitLen >> (i * 8));
    }

    // Process each 64-byte chunk
    for (size_t chunk = 0; chunk < newLen; chunk += 64) {
        uint32_t w[64];

        // Break chunk into sixteen 32-bit big-endian words
        for (int i = 0; i < 16; ++i) {
            w[i] = (static_cast<uint32_t>(msg[chunk + i*4]) << 24) |
                   (static_cast<uint32_t>(msg[chunk + i*4 + 1]) << 16) |
                   (static_cast<uint32_t>(msg[chunk + i*4 + 2]) << 8) |
                   (static_cast<uint32_t>(msg[chunk + i*4 + 3]));
        }

        // Extend to 64 words
        for (int i = 16; i < 64; ++i) {
            w[i] = gamma1(w[i-2]) + w[i-7] + gamma0(w[i-15]) + w[i-16];
        }

        // Working variables
        uint32_t a = h[0], b = h[1], c = h[2], d = h[3];
        uint32_t e = h[4], f = h[5], g = h[6], hh = h[7];

        // Compression
        for (int i = 0; i < 64; ++i) {
            uint32_t t1 = hh + sigma1(e) + ch(e, f, g) + K[i] + w[i];
            uint32_t t2 = sigma0(a) + maj(a, b, c);
            hh = g; g = f; f = e; e = d + t1;
            d = c; c = b; b = a; a = t1 + t2;
        }

        // Add to hash
        h[0] += a; h[1] += b; h[2] += c; h[3] += d;
        h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
    }

    delete[] msg;

    // Output hash as big-endian
    for (int i = 0; i < 8; ++i) {
        out[i*4] = static_cast<uint8_t>(h[i] >> 24);
        out[i*4 + 1] = static_cast<uint8_t>(h[i] >> 16);
        out[i*4 + 2] = static_cast<uint8_t>(h[i] >> 8);
        out[i*4 + 3] = static_cast<uint8_t>(h[i]);
    }
#endif
}

void SignatureVerifier::bytesToHex(const uint8_t* bytes, size_t len, char* hex) {
    static const char hexChars[] = "0123456789abcdef";
    for (size_t i = 0; i < len; ++i) {
        hex[i * 2] = hexChars[(bytes[i] >> 4) & 0x0F];
        hex[i * 2 + 1] = hexChars[bytes[i] & 0x0F];
    }
}

bool SignatureVerifier::hexToBytes(const char* hex, size_t hexLen, uint8_t* bytes, size_t bytesLen) {
    if (hexLen != bytesLen * 2) {
        return false;
    }

    auto hexValue = [](char c) -> int {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        return -1;
    };

    for (size_t i = 0; i < bytesLen; ++i) {
        int hi = hexValue(hex[i * 2]);
        int lo = hexValue(hex[i * 2 + 1]);
        if (hi < 0 || lo < 0) {
            return false;
        }
        bytes[i] = static_cast<uint8_t>((hi << 4) | lo);
    }

    return true;
}

} // namespace mara
