// include/motor/ActuatorConfig.h
// Auto-configuration for actuators from Pins:: constants
//
// Reduces friction by automatically calling attach() with pins
// defined in PinConfig.h. No more manual wiring needed.

#pragma once

#include "config/PinConfig.h"
#include "config/FeatureFlags.h"

namespace mara {

/// Default encoder ticks per revolution
/// TODO: Make this configurable per-motor via MaraConfig
constexpr float DEFAULT_ENCODER_TICKS_PER_REV = 1632.67f;

/// Auto-configure DC motors from Pins:: constants
/// Call this in SetupMotors instead of manual attach() calls
///
/// Expected pin naming in pins.json:
///   Motor 0: MOTOR_LEFT_IN1, MOTOR_LEFT_IN2, MOTOR_LEFT_PWM
///   Motor 1: MOTOR_RIGHT_IN1, MOTOR_RIGHT_IN2, MOTOR_RIGHT_PWM
///
/// Returns number of motors configured
template<typename DcMotorManagerT>
int autoConfigureDcMotors(DcMotorManagerT& dcMotor) {
    int count = 0;
#if HAS_DC_MOTOR
    // Motor 0: Left motor
    if (dcMotor.attach(0,
            Pins::MOTOR_LEFT_IN1,
            Pins::MOTOR_LEFT_IN2,
            Pins::MOTOR_LEFT_PWM,
            0,      // LEDC channel 0
            15000,  // PWM frequency
            12)) {  // Resolution bits
        // Configure encoder for velocity feedback (motor 0 uses encoder 0)
        dcMotor.configureEncoder(0, 0, DEFAULT_ENCODER_TICKS_PER_REV);
        count++;
    }

    // Motor 1: Right motor (compile-time check for existence)
    // Note: These are constexpr, so we just try to use them
    // and rely on the stub returning false if not configured
#endif
    return count;
}

/// Auto-configure servos from Pins:: constants
template<typename ServoManagerT>
void autoConfigureServos(ServoManagerT& servo) {
#if HAS_SERVO
    #ifdef Pins_SERVO0_SIG
    servo.attach(0, Pins::SERVO0_SIG);
    #endif
    #ifdef Pins_SERVO1_SIG
    servo.attach(1, Pins::SERVO1_SIG);
    #elif defined(Pins_SERVO1_PIN)
    servo.attach(1, Pins::SERVO1_SIG);
    #else
    // Try legacy naming
    servo.attach(0, Pins::SERVO1_SIG);
    #endif
    #ifdef Pins_SERVO2_SIG
    servo.attach(2, Pins::SERVO2_SIG);
    #endif
    #ifdef Pins_SERVO3_SIG
    servo.attach(3, Pins::SERVO3_SIG);
    #endif
#endif
}

/// Auto-configure steppers from Pins:: constants
template<typename StepperManagerT>
void autoConfigureSteppers(StepperManagerT& stepper) {
#if HAS_STEPPER
    #ifdef Pins_STEPPER0_STEP
    stepper.attach(0,
        Pins::STEPPER0_STEP,
        Pins::STEPPER0_DIR,
        Pins::STEPPER0_EN
    );
    #endif

    #ifdef Pins_STEPPER1_STEP
    stepper.attach(1,
        Pins::STEPPER1_STEP,
        Pins::STEPPER1_DIR,
        Pins::STEPPER1_EN
    );
    #endif
#endif
}

/// Auto-configure encoders from Pins:: constants
template<typename EncoderManagerT>
void autoConfigureEncoders(EncoderManagerT& encoder) {
#if HAS_ENCODER
    #ifdef Pins_ENC0_A
    encoder.attach(0, Pins::ENC0_A, Pins::ENC0_B);
    #endif

    #ifdef Pins_ENC1_A
    encoder.attach(1, Pins::ENC1_A, Pins::ENC1_B);
    #endif
#endif
}

/// Auto-configure all actuators at once
struct ActuatorAutoConfig {
    template<typename DcT, typename ServoT, typename StepperT, typename EncT>
    static void configureAll(DcT& dc, ServoT& servo, StepperT& stepper, EncT& encoder) {
        autoConfigureDcMotors(dc);
        autoConfigureServos(servo);
        autoConfigureSteppers(stepper);
        autoConfigureEncoders(encoder);
    }
};

} // namespace mara
