// include/security/SignatureVerifier.h
// HMAC-SHA256 signature verification for signed state transitions

#pragma once

#include <stdint.h>
#include <stddef.h>

namespace mara {

/**
 * SignatureVerifier - Verifies HMAC-SHA256 signatures on command payloads.
 *
 * Used to gate state transitions (ARM, ACTIVATE, etc.) so only authorized
 * hosts can control the robot. Without a valid signing key, hosts are
 * limited to read-only operations (telemetry, queries, ping).
 *
 * Key provisioning:
 * - First key: Allowed unconditionally (no key set yet)
 * - Key rotation: Requires current key to sign new key payload
 * - Clear key: Requires physical reset (hold button 5s on boot)
 *
 * Security model:
 * - IDLE: Read-only (no key needed)
 * - State transitions require signature if key is set
 * - Worst case for compromised session: observer, not actor
 */
class SignatureVerifier {
public:
    static constexpr size_t KEY_SIZE = 32;       // 256-bit key
    static constexpr size_t SIGNATURE_SIZE = 64; // Hex-encoded HMAC-SHA256

    SignatureVerifier() = default;

    /**
     * Set the pre-shared key for HMAC verification.
     * @param key Pointer to key bytes
     * @param len Length of key (should be KEY_SIZE for full security)
     */
    void setKey(const uint8_t* key, size_t len);

    /**
     * Clear the signing key (disables signature checking).
     */
    void clearKey();

    /**
     * Check if a signing key is configured.
     */
    bool hasKey() const { return hasKey_; }

    /**
     * Verify HMAC-SHA256 signature on a payload.
     *
     * @param payload The JSON payload string (canonical form, sorted keys)
     * @param payloadLen Length of payload
     * @param signature Hex-encoded HMAC-SHA256 signature (64 chars)
     * @return true if signature is valid, false otherwise
     */
    bool verify(const char* payload, size_t payloadLen, const char* signature) const;

    /**
     * Compute HMAC-SHA256 signature for a payload.
     * Useful for testing and key rotation.
     *
     * @param payload The JSON payload string
     * @param payloadLen Length of payload
     * @param outSignature Buffer to write hex-encoded signature (must be >= 65 bytes)
     * @return true on success, false if no key set
     */
    bool sign(const char* payload, size_t payloadLen, char* outSignature) const;

private:
    uint8_t key_[KEY_SIZE] = {0};
    size_t keyLen_ = 0;
    bool hasKey_ = false;

    // HMAC-SHA256 implementation
    void hmacSha256(const uint8_t* key, size_t keyLen,
                    const uint8_t* data, size_t dataLen,
                    uint8_t* out) const;

    // SHA256 hash
    void sha256(const uint8_t* data, size_t len, uint8_t* out) const;

    // Hex encoding
    static void bytesToHex(const uint8_t* bytes, size_t len, char* hex);
    static bool hexToBytes(const char* hex, size_t hexLen, uint8_t* bytes, size_t bytesLen);
};

} // namespace mara
