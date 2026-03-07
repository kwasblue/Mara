#pragma once
#include <Arduino.h>

namespace audio {

struct BiquadCoeffs {
    float b0, b1, b2;
    float a1, a2; // a0 is assumed normalized to 1
};

enum class BiquadType {
    HighPass,
    LowShelf,
    Peaking,
    HighShelf
};

// RBJ-style cookbook designs.
// freq in Hz, sr in Hz, Q dimensionless, db can be +/- for EQ types.
BiquadCoeffs designHighPass(float sr, float freq, float Q);
BiquadCoeffs designPeaking(float sr, float freq, float Q, float db);
BiquadCoeffs designLowShelf(float sr, float freq, float Q, float db);
BiquadCoeffs designHighShelf(float sr, float freq, float Q, float db);

} // namespace audio
