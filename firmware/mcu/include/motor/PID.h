// include/core/PID.h
#pragma once

class PID {
public:
    PID(float kp = 0.0f, float ki = 0.0f, float kd = 0.0f)
        : kp_(kp), ki_(ki), kd_(kd),
          prevError_(0.0f), integral_(0.0f),
          outMin_(-1.0f), outMax_(1.0f),
          integratorMin_(-1.0f), integratorMax_(1.0f),
          derivativeFilterCoeff_(0.0f),
          prevMeasurement_(0.0f),
          prevDeriv_(0.0f)
    {}

    void setGains(float kp, float ki, float kd) {
        kp_ = kp; ki_ = ki; kd_ = kd;
    }

    void setOutputLimits(float minVal, float maxVal) {
        outMin_ = minVal;
        outMax_ = maxVal;
    }

    // clamp integral term independent of output clamp (anti-windup)
    void setIntegratorLimits(float minVal, float maxVal) {
        integratorMin_ = minVal;
        integratorMax_ = maxVal;
    }

    // 0 = no filtering, closer to 1 = heavier low-pass on derivative
    void setDerivativeFilter(float alpha) {
        if (alpha < 0.0f) alpha = 0.0f;
        if (alpha > 1.0f) alpha = 1.0f;
        derivativeFilterCoeff_ = alpha;
    }

    void reset() {
        prevError_      = 0.0f;
        integral_       = 0.0f;
        prevMeasurement_= 0.0f;
        prevDeriv_      = 0.0f;
    }

    // target = desired value (rad/s), measurement = encoder-derived value, dt in seconds
    float compute(float target, float measurement, float dt) {
        if (dt <= 0.0f) {
            return clamp(lastOutput_, outMin_, outMax_);
        }

        float error = target - measurement;

        // Proportional
        float P = kp_ * error;

        // Integral with anti-windup
        integral_ += error * dt * ki_;
        integral_ = clamp(integral_, integratorMin_, integratorMax_);
        float I = integral_;

        // Derivative on measurement (less noise)
        float derivRaw = (measurement - prevMeasurement_) / dt;
        float deriv = derivativeFilterCoeff_ * prevDeriv_ +
                      (1.0f - derivativeFilterCoeff_) * derivRaw;
        float D = -kd_ * deriv;  // minus sign because derivative on measurement

        float out = P + I + D;
        out = clamp(out, outMin_, outMax_);

        prevError_       = error;
        prevMeasurement_ = measurement;
        prevDeriv_       = deriv;
        lastOutput_      = out;
        return out;
    }

private:
    float kp_, ki_, kd_;
    float prevError_;
    float integral_;
    float outMin_, outMax_;
    float integratorMin_, integratorMax_;

    float derivativeFilterCoeff_;
    float prevMeasurement_;
    float prevDeriv_;

    float lastOutput_ = 0.0f;

    static float clamp(float v, float lo, float hi) {
        if (v < lo) return lo;
        if (v > hi) return hi;
        return v;
    }
};
