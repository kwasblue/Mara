// test/test_pid_controller/test_pid_controller.cpp

#include <unity.h>
#include "motor/PID.h"

static PID pid;

void setUp() { 
    pid.setGains(0.0f, 0.0f, 0.0f);
    pid.reset(); 
}
void tearDown() {}

void test_proportional_only() {
    pid.setGains(1.0f, 0.0f, 0.0f);
    pid.setOutputLimits(-10.0f, 10.0f);
    
    float out = pid.compute(5.0f, 0.0f, 0.01f);  // target=5, meas=0, error=5
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 5.0f, out);
}

void test_proportional_negative_error() {
    pid.setGains(2.0f, 0.0f, 0.0f);
    pid.setOutputLimits(-10.0f, 10.0f);
    
    float out = pid.compute(0.0f, 5.0f, 0.01f);  // target=0, meas=5, error=-5
    TEST_ASSERT_FLOAT_WITHIN(0.01f, -10.0f, out);  // 2*(-5) = -10
}

void test_integral_accumulates() {
    pid.setGains(0.0f, 10.0f, 0.0f);
    pid.setOutputLimits(-100.0f, 100.0f);
    pid.setIntegratorLimits(-100.0f, 100.0f);
    
    // Constant error of 1.0 for 10 steps at dt=0.1
    for (int i = 0; i < 10; i++) {
        pid.compute(1.0f, 0.0f, 0.1f);
    }
    float out = pid.compute(1.0f, 0.0f, 0.1f);
    // Integral should be ~11 * 0.1 * 1.0 * 10 = 11.0
    TEST_ASSERT_FLOAT_WITHIN(1.0f, 11.0f, out);
}

void test_output_clamping() {
    pid.setGains(100.0f, 0.0f, 0.0f);
    pid.setOutputLimits(-1.0f, 1.0f);
    
    float out = pid.compute(10.0f, 0.0f, 0.01f);  // Would be 1000 without clamp
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.0f, out);
}

void test_output_clamping_negative() {
    pid.setGains(100.0f, 0.0f, 0.0f);
    pid.setOutputLimits(-1.0f, 1.0f);
    
    float out = pid.compute(-10.0f, 0.0f, 0.01f);  // Would be -1000 without clamp
    TEST_ASSERT_FLOAT_WITHIN(0.001f, -1.0f, out);
}

void test_reset_clears_integrator() {
    pid.setGains(0.0f, 10.0f, 0.0f);
    pid.setOutputLimits(-100.0f, 100.0f);
    pid.setIntegratorLimits(-100.0f, 100.0f);
    
    for (int i = 0; i < 10; i++) {
        pid.compute(1.0f, 0.0f, 0.1f);
    }
    pid.reset();
    float out = pid.compute(1.0f, 0.0f, 0.1f);
    // Just one step of integral: 0.1 * 1.0 * 10 = 1.0
    TEST_ASSERT_FLOAT_WITHIN(0.5f, 1.0f, out);
}

void test_derivative_opposes_change() {
    pid.setGains(0.0f, 0.0f, 1.0f);
    pid.setOutputLimits(-100.0f, 100.0f);
    
    // First call establishes baseline
    pid.compute(0.0f, 0.0f, 0.1f);
    
    // Measurement suddenly jumps to 10 -> derivative term should be negative
    float out = pid.compute(0.0f, 10.0f, 0.1f);
    TEST_ASSERT_TRUE(out < 0);  // Derivative opposes measurement increase
}

void test_zero_dt_safe() {
    pid.setGains(1.0f, 1.0f, 1.0f);
    pid.setOutputLimits(-10.0f, 10.0f);
    
    // Should not crash or produce NaN
    float out = pid.compute(5.0f, 0.0f, 0.0f);
    TEST_ASSERT_FALSE(isnan(out));
    TEST_ASSERT_FALSE(isinf(out));
}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_proportional_only);
    RUN_TEST(test_proportional_negative_error);
    RUN_TEST(test_integral_accumulates);
    RUN_TEST(test_output_clamping);
    RUN_TEST(test_output_clamping_negative);
    RUN_TEST(test_reset_clears_integrator);
    RUN_TEST(test_derivative_opposes_change);
    RUN_TEST(test_zero_dt_safe);
    return UNITY_END();
}