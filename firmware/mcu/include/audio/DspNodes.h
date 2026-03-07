#pragma once
#include <Arduino.h>
#include <vector>
#include <cmath>

#include "audio/Biquad.h"
#include "audio/BiquadDesign.h"

namespace audio {

class DspNode {
public:
    virtual ~DspNode() = default;
    virtual void process(float* interleaved, size_t frames, int ch) = 0;
};

// -------------------- Bypass --------------------
class BypassNode : public DspNode {
public:
    void process(float*, size_t, int) override {}
};

// -------------------- Gain --------------------
class GainNode : public DspNode {
public:
    explicit GainNode(float db) {
        gain_ = powf(10.0f, db / 20.0f);
    }
    void process(float* x, size_t frames, int ch) override {
        const size_t n = frames * ch;
        for (size_t i = 0; i < n; i++) x[i] *= gain_;
    }
private:
    float gain_;
};

// -------------------- Biquad EQ/Filter Node --------------------
class BiquadNode : public DspNode {
public:
    BiquadNode(const BiquadCoeffs& c, int ch)
        : biquad_(c.b0, c.b1, c.b2, c.a1, c.a2, ch) {}

    void process(float* x, size_t frames, int ch) override {
        for (size_t f = 0; f < frames; f++) {
            for (int c = 0; c < ch; c++) {
                float& s = x[f * ch + c];
                s = biquad_.process(s, c);
            }
        }
    }

private:
    Biquad biquad_;
};

// -------------------- Simple Peak Limiter --------------------
// MVP limiter: fast attack, smooth release.
class PeakLimiterNode : public DspNode {
public:
    PeakLimiterNode(float threshold_db, float attack_ms, float release_ms, int sr, int ch)
        : ch_(ch) {

        threshold_ = powf(10.0f, threshold_db / 20.0f);
        if (threshold_ < 0.001f) threshold_ = 0.001f;

        const float attack_samples  = fmaxf(1.0f, (attack_ms  * sr) / 1000.0f);
        const float release_samples = fmaxf(1.0f, (release_ms * sr) / 1000.0f);

        // coeff ~ exp(-1/N)
        attack_coeff_  = expf(-1.0f / attack_samples);
        release_coeff_ = expf(-1.0f / release_samples);

        gain_state_.assign(ch_, 1.0f);
    }

    void process(float* x, size_t frames, int ch) override {
        (void)ch; // trust ch_ init

        for (size_t f = 0; f < frames; f++) {
            for (int c = 0; c < ch_; c++) {
                float& s = x[f * ch_ + c];
                const float a = fabsf(s);

                float target = 1.0f;
                if (a > threshold_) {
                    target = threshold_ / a;
                }

                float& g = gain_state_[c];

                if (target < g) {
                    // Attack: move quickly toward more limiting
                    g = (attack_coeff_ * g) + ((1.0f - attack_coeff_) * target);
                } else {
                    // Release: move slowly back toward 1
                    g = (release_coeff_ * g) + ((1.0f - release_coeff_) * target);
                }

                s *= g;
            }
        }
    }

private:
    int ch_;
    float threshold_;
    float attack_coeff_;
    float release_coeff_;
    std::vector<float> gain_state_;
}; 

}// namespace audio
