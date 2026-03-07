#include "audio/BiquadDesign.h"
#include <math.h>

namespace audio {

static inline BiquadCoeffs normalize(float b0, float b1, float b2,
                                     float a0, float a1, float a2) {
    BiquadCoeffs c;
    const float invA0 = 1.0f / a0;
    c.b0 = b0 * invA0;
    c.b1 = b1 * invA0;
    c.b2 = b2 * invA0;
    c.a1 = a1 * invA0;
    c.a2 = a2 * invA0;
    return c;
}

BiquadCoeffs designHighPass(float sr, float freq, float Q) {
    const float w0 = 2.0f * (float)M_PI * (freq / sr);
    const float cosw0 = cosf(w0);
    const float sinw0 = sinf(w0);
    const float alpha = sinw0 / (2.0f * Q);

    const float b0 =  (1.0f + cosw0) * 0.5f;
    const float b1 = -(1.0f + cosw0);
    const float b2 =  (1.0f + cosw0) * 0.5f;

    const float a0 =  1.0f + alpha;
    const float a1 = -2.0f * cosw0;
    const float a2 =  1.0f - alpha;

    return normalize(b0, b1, b2, a0, a1, a2);
}

BiquadCoeffs designPeaking(float sr, float freq, float Q, float db) {
    const float A  = powf(10.0f, db / 40.0f);
    const float w0 = 2.0f * (float)M_PI * (freq / sr);
    const float cosw0 = cosf(w0);
    const float sinw0 = sinf(w0);
    const float alpha = sinw0 / (2.0f * Q);

    const float b0 = 1.0f + alpha * A;
    const float b1 = -2.0f * cosw0;
    const float b2 = 1.0f - alpha * A;

    const float a0 = 1.0f + alpha / A;
    const float a1 = -2.0f * cosw0;
    const float a2 = 1.0f - alpha / A;

    return normalize(b0, b1, b2, a0, a1, a2);
}

BiquadCoeffs designLowShelf(float sr, float freq, float Q, float db) {
    const float A  = powf(10.0f, db / 40.0f);
    const float w0 = 2.0f * (float)M_PI * (freq / sr);
    const float cosw0 = cosf(w0);
    const float sinw0 = sinf(w0);

    // RBJ low-shelf uses S (slope). We'll map Q -> S approximately.
    // MVP simplification: treat Q as slope control via alpha-like term.
    const float alpha = sinw0 / (2.0f * Q);
    const float sqrtA = sqrtf(A);

    const float b0 =    A*((A+1.0f) - (A-1.0f)*cosw0 + 2.0f*sqrtA*alpha);
    const float b1 =  2.0f*A*((A-1.0f) - (A+1.0f)*cosw0);
    const float b2 =    A*((A+1.0f) - (A-1.0f)*cosw0 - 2.0f*sqrtA*alpha);

    const float a0 =        (A+1.0f) + (A-1.0f)*cosw0 + 2.0f*sqrtA*alpha;
    const float a1 =   -2.0f*((A-1.0f) + (A+1.0f)*cosw0);
    const float a2 =        (A+1.0f) + (A-1.0f)*cosw0 - 2.0f*sqrtA*alpha;

    return normalize(b0, b1, b2, a0, a1, a2);
}

BiquadCoeffs designHighShelf(float sr, float freq, float Q, float db) {
    const float A  = powf(10.0f, db / 40.0f);
    const float w0 = 2.0f * (float)M_PI * (freq / sr);
    const float cosw0 = cosf(w0);
    const float sinw0 = sinf(w0);

    // Same MVP simplification as low-shelf
    const float alpha = sinw0 / (2.0f * Q);
    const float sqrtA = sqrtf(A);

    const float b0 =    A*((A+1.0f) + (A-1.0f)*cosw0 + 2.0f*sqrtA*alpha);
    const float b1 = -2.0f*A*((A-1.0f) + (A+1.0f)*cosw0);
    const float b2 =    A*((A+1.0f) + (A-1.0f)*cosw0 - 2.0f*sqrtA*alpha);

    const float a0 =        (A+1.0f) - (A-1.0f)*cosw0 + 2.0f*sqrtA*alpha;
    const float a1 =    2.0f*((A-1.0f) - (A+1.0f)*cosw0);
    const float a2 =        (A+1.0f) - (A-1.0f)*cosw0 - 2.0f*sqrtA*alpha;

    return normalize(b0, b1, b2, a0, a1, a2);
}

} // namespace audio
