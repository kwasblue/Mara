#pragma once

class Servo {
public:
  Servo() = default;

  bool attach(int pin, int minUs = 500, int maxUs = 2500) {
    (void)pin; (void)minUs; (void)maxUs;
    return true;
  }

  void detach() {}

  void write(float angle) { (void)angle; }

  void writeMicroseconds(int us) { (void)us; }
};
