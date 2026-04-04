// include/core/SessionManager.h
// Session ownership management - only one host can control at a time

#pragma once

#include <stdint.h>

namespace mara {

/**
 * SessionManager - Manages single-controller session ownership.
 *
 * Only one host can own the session at a time. Other hosts become observers
 * with read-only access (telemetry, queries, ping).
 *
 * Session is claimed on first heartbeat with a client ID.
 * Session is released on timeout or explicit release command.
 *
 * Timeout: 2-3 seconds (short enough for rapid reconnects during dev)
 */
class SessionManager {
public:
    static constexpr uint32_t SESSION_TIMEOUT_MS = 2500;  // 2.5 seconds

    SessionManager() = default;

    /**
     * Attempt to claim the session for a client.
     *
     * @param clientId The client's unique ID
     * @param now_ms Current time in milliseconds
     * @return true if session claimed or already owned by this client
     */
    bool claimSession(uint32_t clientId, uint32_t now_ms);

    /**
     * Check if any session is currently active.
     */
    bool hasActiveSession() const { return active_; }

    /**
     * Check if a specific client owns the session.
     */
    bool isSessionOwner(uint32_t clientId) const {
        return active_ && ownerId_ == clientId;
    }

    /**
     * Release the current session.
     */
    void releaseSession();

    /**
     * Check for session timeout and release if expired.
     *
     * @param now_ms Current time in milliseconds
     * @return true if session was expired and released
     */
    bool checkTimeout(uint32_t now_ms);

    /**
     * Update last heartbeat time for the session owner.
     *
     * @param clientId The client's unique ID (must be session owner)
     * @param now_ms Current time in milliseconds
     */
    void onHeartbeat(uint32_t clientId, uint32_t now_ms);

    /**
     * Get the current session owner ID.
     * Returns 0 if no active session.
     */
    uint32_t sessionOwnerId() const { return active_ ? ownerId_ : 0; }

    /**
     * Get time since last heartbeat in milliseconds.
     */
    uint32_t timeSinceLastHeartbeat(uint32_t now_ms) const {
        if (!active_) return 0;
        return (now_ms >= lastHeartbeatMs_) ? (now_ms - lastHeartbeatMs_) : 0;
    }

private:
    uint32_t ownerId_ = 0;
    uint32_t lastHeartbeatMs_ = 0;
    bool active_ = false;
};

} // namespace mara
