// src/core/SessionManager.cpp
// Session ownership management implementation

#include "core/SessionManager.h"

namespace mara {

bool SessionManager::claimSession(uint32_t clientId, uint32_t now_ms) {
    // Check for stale session first
    checkTimeout(now_ms);

    // No active session - claim it
    if (!active_) {
        ownerId_ = clientId;
        lastHeartbeatMs_ = now_ms;
        active_ = true;
        return true;
    }

    // Already owner
    if (ownerId_ == clientId) {
        lastHeartbeatMs_ = now_ms;
        return true;
    }

    // Another client owns the session
    return false;
}

void SessionManager::releaseSession() {
    ownerId_ = 0;
    lastHeartbeatMs_ = 0;
    active_ = false;
}

bool SessionManager::checkTimeout(uint32_t now_ms) {
    if (!active_) {
        return false;
    }

    uint32_t elapsed = (now_ms >= lastHeartbeatMs_) ?
                       (now_ms - lastHeartbeatMs_) : 0;

    if (elapsed > SESSION_TIMEOUT_MS) {
        releaseSession();
        return true;
    }

    return false;
}

void SessionManager::onHeartbeat(uint32_t clientId, uint32_t now_ms) {
    if (active_ && ownerId_ == clientId) {
        lastHeartbeatMs_ = now_ms;
    }
}

} // namespace mara
