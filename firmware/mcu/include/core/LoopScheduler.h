#pragma once
#include <stdint.h>

class LoopScheduler {
public:
  explicit LoopScheduler(uint32_t period_ms = 20)
  : period_ms_(period_ms), last_ms_(0) {}

  void setPeriodMs(uint32_t p) { period_ms_ = (p == 0 ? 1 : p); }

  // returns true if it's time to run
  bool tick(uint32_t now_ms) {
    if ((uint32_t)(now_ms - last_ms_) >= period_ms_) {
      last_ms_ = now_ms;
      return true;
    }
    return false;
  }

private:
  uint32_t period_ms_;
  uint32_t last_ms_;
};
