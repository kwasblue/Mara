#include <Arduino.h>

// Unity provides these when you include unity.h and call UNITY_BEGIN/RUN_TEST/UNITY_END.
// But Arduino still needs setup/loop symbols to link.

void setup() {
  // Most PlatformIO Unity tests don’t run from here; they run from main in the framework
  // or the PIO test harness. But we must satisfy the linker.
}

void loop() {
  // nothing
  delay(1000);
}
