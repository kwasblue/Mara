// include/hal/linux/LinuxCriticalSection.h
// Linux critical section implementation using pthread_mutex
//
// Provides spinlock-like behavior via pthread_mutex with PTHREAD_MUTEX_ADAPTIVE_NP.
#pragma once

#include "../ICriticalSection.h"
#include <pthread.h>
#include <cstring>
#include <map>
#include <mutex>

namespace hal {

/// Linux critical section using pthread_mutex
///
/// Provides thread-safe critical sections via pthread mutexes.
/// On Linux, uses PTHREAD_MUTEX_ADAPTIVE_NP for spinlock-like behavior.
///
/// Note: ISR variants behave the same as normal variants on Linux,
/// since there's no true ISR context in userspace.
class LinuxCriticalSection : public ICriticalSection {
public:
    LinuxCriticalSection() = default;
    ~LinuxCriticalSection() = default;

    void initSpinlock(SpinlockHandle& lock) override {
        // Initialize pthread mutex - allocate separately due to size
        pthread_mutexattr_t attr;
        pthread_mutexattr_init(&attr);
        // Use adaptive mutex for spinlock-like behavior on Linux
        // Falls back to regular mutex if PTHREAD_MUTEX_ADAPTIVE_NP not available
#ifdef PTHREAD_MUTEX_ADAPTIVE_NP
        pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_ADAPTIVE_NP);
#else
        pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_NORMAL);
#endif
        pthread_mutex_t* mutex = createMutex(lock);
        pthread_mutex_init(mutex, &attr);
        pthread_mutexattr_destroy(&attr);
    }

    void enterCritical(SpinlockHandle& lock) override {
        pthread_mutex_t* mutex = getMutex(lock);
        pthread_mutex_lock(mutex);
    }

    void exitCritical(SpinlockHandle& lock) override {
        pthread_mutex_t* mutex = getMutex(lock);
        pthread_mutex_unlock(mutex);
    }

    void enterCriticalISR(SpinlockHandle& lock) override {
        // On Linux userspace, ISR context doesn't exist.
        // Behave the same as regular critical section.
        enterCritical(lock);
    }

    void exitCriticalISR(SpinlockHandle& lock) override {
        // On Linux userspace, ISR context doesn't exist.
        // Behave the same as regular critical section.
        exitCritical(lock);
    }

private:
    // On Linux (glibc), pthread_mutex_t is typically 40 bytes.
    // SpinlockHandle has 16 bytes storage. We use separate allocation.
    // This map tracks the actual mutex per handle address.
    static inline std::map<void*, pthread_mutex_t*> mutexMap_;
    static inline std::mutex mapMutex_;

    /// Get or create pthread_mutex_t for this SpinlockHandle
    static pthread_mutex_t* getMutex(SpinlockHandle& lock) {
        // Use handle address as key
        void* key = lock.storage;
        std::lock_guard<std::mutex> guard(mapMutex_);
        auto it = mutexMap_.find(key);
        if (it != mutexMap_.end()) {
            return it->second;
        }
        return nullptr;
    }

    static pthread_mutex_t* createMutex(SpinlockHandle& lock) {
        void* key = lock.storage;
        std::lock_guard<std::mutex> guard(mapMutex_);
        auto* mutex = new pthread_mutex_t;
        mutexMap_[key] = mutex;
        return mutex;
    }
};

} // namespace hal
