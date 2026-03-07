#pragma once

// If unit tests (or any other translation unit) define these before including Debug.h,
// do NOT redefine them here.

#ifndef DBG_PRINT
  #define DBG_PRINT(...)   do {} while (0)
#endif

#ifndef DBG_PRINTLN
  #define DBG_PRINTLN(...) do {} while (0)
#endif

#ifndef DBG_PRINTF
  #define DBG_PRINTF(...)  do {} while (0)
#endif
