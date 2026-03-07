// src/core/SignalBus.cpp
// Signal routing system implementation

#include "config/FeatureFlags.h"

#if HAS_SIGNAL_BUS

#include "control/SignalBus.h"
#include "core/CriticalSection.h"
#include <cstring>

int SignalBus::indexOf_(uint16_t id) const {
    // O(1) lookup using cached map
    auto it = idToIndex_.find(id);
    if (it != idToIndex_.end()) {
        return static_cast<int>(it->second);
    }
    return -1;
}

bool SignalBus::define(uint16_t id, const char* name, Kind kind, float initial) {
    // Check if already exists using O(1) lookup
    auto it = idToIndex_.find(id);
    if (it != idToIndex_.end()) {
        // Update existing signal (idempotent)
        auto& d = signals_[it->second];
        d.kind = kind;
        d.value = initial;
        d.ts_ms = 0;
        if (name && name[0] != '\0') {
            strncpy(d.name, name, NAME_MAX_LEN);
            d.name[NAME_MAX_LEN] = '\0';
        }
        return true;
    }

    // Check capacity (optional safety limit)
    if (signals_.size() >= NAME_MAX_LEN) return false;

    // Create new signal
    SignalDef d;
    d.id = id;
    d.kind = kind;
    d.value = initial;
    d.ts_ms = 0;

    if (name && name[0] != '\0') {
        strncpy(d.name, name, NAME_MAX_LEN);
        d.name[NAME_MAX_LEN] = '\0';
    } else {
        d.name[0] = '\0';
    }

    // Add to vector and update lookup map
    size_t newIndex = signals_.size();
    signals_.push_back(d);
    idToIndex_[id] = newIndex;
    return true;
}

bool SignalBus::exists(uint16_t id) const {
    return indexOf_(id) >= 0;
}

bool SignalBus::set(uint16_t id, float v, uint32_t now_ms) {
    mara::CriticalSection lock(lock_);
    int idx = indexOf_(id);
    if (idx < 0) {
        return false;
    }
    auto& sig = signals_[static_cast<size_t>(idx)];
    sig.value = v;
    sig.ts_ms = now_ms;
    sig.last_set_ms = now_ms;
    return true;
}

SignalBus::SetResult SignalBus::setWithRateLimit(uint16_t id, float v, uint32_t now_ms) {
    mara::CriticalSection lock(lock_);
    int idx = indexOf_(id);
    if (idx < 0) {
        return SetResult::SIGNAL_NOT_FOUND;
    }

    auto& sig = signals_[static_cast<size_t>(idx)];

    // Check minimum interval
    if (global_min_interval_ms_ > 0) {
        uint32_t elapsed = now_ms - sig.last_set_ms;
        if (elapsed < global_min_interval_ms_) {
            return SetResult::RATE_LIMITED_TIME;
        }
    }

    // Check max updates per second
    if (global_max_updates_per_sec_ > 0) {
        // Reset counter if new second window
        if (now_ms - sig.rate_window_start >= 1000) {
            sig.rate_window_start = now_ms;
            sig.updates_this_sec = 0;
        }
        if (sig.updates_this_sec >= global_max_updates_per_sec_) {
            return SetResult::RATE_LIMITED_COUNT;
        }
        sig.updates_this_sec++;
    }

    // Apply the update
    sig.value = v;
    sig.ts_ms = now_ms;
    sig.last_set_ms = now_ms;
    return SetResult::OK;
}

void SignalBus::setGlobalRateLimit(uint32_t min_interval_ms, uint16_t max_updates_per_sec) {
    global_min_interval_ms_ = min_interval_ms;
    global_max_updates_per_sec_ = max_updates_per_sec;
}

bool SignalBus::get(uint16_t id, float& out) const {
    mara::CriticalSection lock(lock_);
    int idx = indexOf_(id);
    if (idx < 0) {
        return false;
    }
    out = signals_[static_cast<size_t>(idx)].value;
    return true;
}

bool SignalBus::getTimestamp(uint16_t id, uint32_t& out) const {
    mara::CriticalSection lock(lock_);
    int idx = indexOf_(id);
    if (idx < 0) {
        return false;
    }
    out = signals_[static_cast<size_t>(idx)].ts_ms;
    return true;
}

bool SignalBus::remove(uint16_t id) {
    auto it = idToIndex_.find(id);
    if (it == idToIndex_.end()) return false;

    size_t idx = it->second;

    // Remove from lookup map
    idToIndex_.erase(it);

    // Erase from vector
    signals_.erase(signals_.begin() + idx);

    // Update indices for all signals after the removed one
    for (auto& pair : idToIndex_) {
        if (pair.second > idx) {
            pair.second--;
        }
    }
    return true;
}

const SignalBus::SignalDef* SignalBus::find(uint16_t id) const {
    int idx = indexOf_(id);
    if (idx < 0) return nullptr;
    return &signals_[static_cast<size_t>(idx)];
}

// -----------------------------------------------------------------------------
// Signal Aliasing Implementation
// -----------------------------------------------------------------------------

bool SignalBus::createAlias(uint16_t id, const char* alias) {
    if (!alias || alias[0] == '\0') return false;
    if (!exists(id)) return false;

    // Check if alias already exists
    for (const auto& a : aliases_) {
        if (strcmp(a.name, alias) == 0) return false;
    }

    Alias a;
    strncpy(a.name, alias, NAME_MAX_LEN);
    a.name[NAME_MAX_LEN] = '\0';
    a.id = id;
    aliases_.push_back(a);
    return true;
}

bool SignalBus::removeAlias(const char* alias) {
    if (!alias) return false;

    for (auto it = aliases_.begin(); it != aliases_.end(); ++it) {
        if (strcmp(it->name, alias) == 0) {
            aliases_.erase(it);
            return true;
        }
    }
    return false;
}

uint16_t SignalBus::resolveId(const char* name) const {
    if (!name || name[0] == '\0') return 0;

    // First, check signal names directly
    for (const auto& s : signals_) {
        if (strcmp(s.name, name) == 0) return s.id;
    }

    // Then check aliases
    for (const auto& a : aliases_) {
        if (strcmp(a.name, name) == 0) return a.id;
    }

    return 0;  // Not found
}

bool SignalBus::getByName(const char* name, float& out) const {
    uint16_t id = resolveId(name);
    if (id == 0) return false;
    return get(id, out);
}

bool SignalBus::setByName(const char* name, float v, uint32_t now_ms) {
    uint16_t id = resolveId(name);
    if (id == 0) return false;
    return set(id, v, now_ms);
}

// -----------------------------------------------------------------------------
// Thread-safe Snapshot
// -----------------------------------------------------------------------------

size_t SignalBus::snapshot(SignalSnapshot* out, size_t max_count) const {
    if (!out || max_count == 0) return 0;

    mara::CriticalSection lock(lock_);
    size_t count = signals_.size();
    if (count > max_count) count = max_count;

    for (size_t i = 0; i < count; ++i) {
        const auto& s = signals_[i];
        out[i].id = s.id;
        out[i].value = s.value;
        out[i].ts_ms = s.ts_ms;
        out[i].kind = s.kind;
    }

    return count;
}

#endif // HAS_SIGNAL_BUS
