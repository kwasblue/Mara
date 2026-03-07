#pragma once

// Fake Arduino header for native tests.
// Must compile in both C and C++ (Unity can compile some parts as C).

#ifdef __cplusplus
  #include <cstdint>
  #include <cstddef>
  #include <chrono>
  using std::uint8_t;
  using std::uint16_t;
  using std::uint32_t;
#else
  #include <stdint.h>
  #include <stddef.h>
  typedef uint8_t  uint8_t;
  typedef uint16_t uint16_t;
  typedef uint32_t uint32_t;
#endif

#ifdef __cplusplus
extern "C" {
#endif

// Basic Arduino constants
static const int LOW         = 0;
static const int HIGH        = 1;
static const int INPUT       = 0;
static const int OUTPUT      = 1;
static const int INPUT_PULLUP= 2;
static const int CHANGE      = 3;

// ESP-IDF-ish placeholder type used in your code
typedef int gpio_num_t;

// Interrupt function pointer
typedef void (*voidFuncPtr)(void);

// GPIO stubs
static inline void pinMode(int pin, int mode) { (void)pin; (void)mode; }
static inline void digitalWrite(int pin, int val) { (void)pin; (void)val; }
static inline int  digitalRead(int pin) { (void)pin; return LOW; }

// Interrupt stubs
static inline int  digitalPinToInterrupt(int pin) { return pin; }
static inline void attachInterrupt(int intr, voidFuncPtr fn, int mode) {
  (void)intr; (void)fn; (void)mode;
}
static inline void noInterrupts(void) {}
static inline void interrupts(void) {}

// Timing stubs
static inline void delayMicroseconds(unsigned int us) { (void)us; }

// pulseIn stub (Ultrasonic uses it)
static inline unsigned long pulseIn(uint8_t pin, uint8_t state, unsigned long timeout) {
  (void)pin; (void)state; (void)timeout;
  return 0UL;
}

// millis() stub (CommandHandler uses it)
#ifdef __cplusplus
static inline unsigned long millis(void) {
  using namespace std::chrono;
  static const auto t0 = steady_clock::now();
  return (unsigned long)duration_cast<milliseconds>(steady_clock::now() - t0).count();
}
#else
static inline unsigned long millis(void) { return 0UL; }
#endif

// LEDC PWM stubs (ESP32 Arduino)
static inline double ledcSetup(int ch, double freq, int res) {
  (void)ch; (void)freq; (void)res;
  return 0.0;
}
static inline void   ledcAttachPin(int pin, int ch) { (void)pin; (void)ch; }
static inline void   ledcWrite(int ch, int duty) { (void)ch; (void)duty; }

#ifdef __cplusplus
} // extern "C"
#endif
