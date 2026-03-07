#pragma once
#include <vector>

namespace audio {

class Biquad {
public:
    Biquad(float b0, float b1, float b2, float a1, float a2, int ch)
        : b0_(b0), b1_(b1), b2_(b2), a1_(a1), a2_(a2),
          z1_(ch, 0.0f), z2_(ch, 0.0f) {}

    inline float process(float x, int c) {
        float y = b0_ * x + z1_[c];
        z1_[c] = b1_ * x - a1_ * y + z2_[c];
        z2_[c] = b2_ * x - a2_ * y;
        return y;
    }

private:
    float b0_, b1_, b2_, a1_, a2_;
    std::vector<float> z1_, z2_;
};

} // namespace audio
