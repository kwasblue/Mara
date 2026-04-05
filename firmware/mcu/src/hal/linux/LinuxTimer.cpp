// src/hal/linux/LinuxTimer.cpp
// Linux timer implementation using timerfd

#include "hal/linux/LinuxTimer.h"

#if PLATFORM_LINUX

#include <sys/timerfd.h>
#include <unistd.h>
#include <cstring>

namespace hal {

LinuxTimer::LinuxTimer() {
    clock_gettime(CLOCK_MONOTONIC, &bootTime_);
}

LinuxTimer::~LinuxTimer() {
    stop();
}

bool LinuxTimer::startRepeating(uint32_t intervalUs, TimerCallback callback) {
    if (running_) {
        stop();
    }

    callback_ = callback;
    repeating_ = true;

    if (!createTimer()) {
        return false;
    }

    if (!setTimer(intervalUs, true)) {
        destroyTimer();
        return false;
    }

    running_ = true;
    timerThread_ = std::thread(&LinuxTimer::timerThreadFunc, this);
    return true;
}

bool LinuxTimer::startOnce(uint32_t delayUs, TimerCallback callback) {
    if (running_) {
        stop();
    }

    callback_ = callback;
    repeating_ = false;

    if (!createTimer()) {
        return false;
    }

    if (!setTimer(delayUs, false)) {
        destroyTimer();
        return false;
    }

    running_ = true;
    timerThread_ = std::thread(&LinuxTimer::timerThreadFunc, this);
    return true;
}

void LinuxTimer::stop() {
    if (!running_) {
        return;
    }

    running_ = false;

    // Disarm the timer to wake the thread
    if (timerFd_ >= 0) {
        struct itimerspec its = {};
        timerfd_settime(timerFd_, 0, &its, nullptr);
    }

    if (timerThread_.joinable()) {
        timerThread_.join();
    }

    destroyTimer();
    callback_ = nullptr;
}

bool LinuxTimer::isRunning() const {
    return running_;
}

uint64_t LinuxTimer::micros() const {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    uint64_t elapsed_ns = (now.tv_sec - bootTime_.tv_sec) * 1000000000ULL +
                          (now.tv_nsec - bootTime_.tv_nsec);
    return elapsed_ns / 1000ULL;
}

uint32_t LinuxTimer::millis() const {
    return static_cast<uint32_t>(micros() / 1000ULL);
}

void LinuxTimer::delayMicros(uint32_t us) {
    struct timespec ts;
    ts.tv_sec = us / 1000000;
    ts.tv_nsec = (us % 1000000) * 1000L;
    clock_nanosleep(CLOCK_MONOTONIC, 0, &ts, nullptr);
}

void LinuxTimer::delayMillis(uint32_t ms) {
    delayMicros(ms * 1000);
}

void LinuxTimer::timerThreadFunc() {
    while (running_) {
        uint64_t expirations;
        ssize_t n = read(timerFd_, &expirations, sizeof(expirations));

        if (n != sizeof(expirations)) {
            // Read error or interrupted
            if (!running_) break;
            continue;
        }

        if (running_ && callback_) {
            callback_();
        }

        if (!repeating_) {
            running_ = false;
            break;
        }
    }
}

bool LinuxTimer::createTimer() {
    timerFd_ = timerfd_create(CLOCK_MONOTONIC, TFD_CLOEXEC);
    return timerFd_ >= 0;
}

void LinuxTimer::destroyTimer() {
    if (timerFd_ >= 0) {
        close(timerFd_);
        timerFd_ = -1;
    }
}

bool LinuxTimer::setTimer(uint32_t delayUs, bool repeating) {
    struct itimerspec its;
    memset(&its, 0, sizeof(its));

    // Initial expiration
    its.it_value.tv_sec = delayUs / 1000000;
    its.it_value.tv_nsec = (delayUs % 1000000) * 1000L;

    // Interval (0 for one-shot)
    if (repeating) {
        its.it_interval = its.it_value;
    }

    return timerfd_settime(timerFd_, 0, &its, nullptr) == 0;
}

} // namespace hal

#endif // PLATFORM_LINUX
