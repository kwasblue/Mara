#include "core/LoopRates.h"

static LoopRates g_rates;

LoopRates& getLoopRates() { return g_rates; }

bool clampHz(uint16_t& hz, uint16_t lo, uint16_t hi) {
  if (hz < lo) { hz = lo; return false; }
  if (hz > hi) { hz = hi; return false; }
  return true;
}
