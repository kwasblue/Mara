#pragma once
#include <stdint.h>

struct LoopRates {
  // Defaults (safe, can tune later)
  uint16_t ctrl_hz   = 50;   // main control update (MotionController.update, etc)
  uint16_t safety_hz = 100;  // safety checks / estop / watchdog style checks
  uint16_t telem_hz  = 10;   // telemetry send interval

  static constexpr uint16_t CTRL_HZ_MIN   = 5;
  static constexpr uint16_t CTRL_HZ_MAX   = 200;

  static constexpr uint16_t SAFETY_HZ_MIN = 20;
  static constexpr uint16_t SAFETY_HZ_MAX = 500;

  static constexpr uint16_t TELEM_HZ_MIN  = 1;
  static constexpr uint16_t TELEM_HZ_MAX  = 50;

  inline uint32_t ctrl_period_ms() const   { return (uint32_t)(1000UL / (ctrl_hz   ? ctrl_hz   : 1)); }
  inline uint32_t safety_period_ms() const { return (uint32_t)(1000UL / (safety_hz ? safety_hz : 1)); }
  inline uint32_t telem_period_ms() const  { return (uint32_t)(1000UL / (telem_hz  ? telem_hz  : 1)); }
};

// Global accessors (simple + stable)
LoopRates& getLoopRates();
bool clampHz(uint16_t& hz, uint16_t lo, uint16_t hi);
