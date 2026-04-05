// include/hal/linux/LinuxTimer.h
// Linux timer implementation using timerfd
//
// Uses timerfd_create() for kernel-based timers with callback support.
#pragma once

#include "../ITimer.h"
#include <cstdint>
#include <thread>
#include <atomic>
#include <ctime>

namespace hal {

/// Linux timer implementation using timerfd
///
/// Provides high-resolution timers via timerfd_create().
/// Callbacks are executed in a dedicated thread.
///
/// Features:
/// - One-shot and repeating timers
/// - Microsecond resolution
/// - Thread-safe callback invocation
class LinuxTimer : public ITimer {
public:
    LinuxTimer();
    ~LinuxTimer();

    bool startRepeating(uint32_t intervalUs, TimerCallback callback) override;
    bool startOnce(uint32_t delayUs, TimerCallback callback) override;
    void stop() override;
    bool isRunning() const override;
    uint64_t micros() const override;
    uint32_t millis() const override;
    void delayMicros(uint32_t us) override;
    void delayMillis(uint32_t ms) override;

private:
    int timerFd_ = -1;
    std::thread timerThread_;
    std::atomic<bool> running_{false};
    TimerCallback callback_ = nullptr;
    bool repeating_ = false;
    struct timespec bootTime_;

    void timerThreadFunc();
    bool createTimer();
    void destroyTimer();
    bool setTimer(uint32_t delayUs, bool repeating);
};

} // namespace hal
