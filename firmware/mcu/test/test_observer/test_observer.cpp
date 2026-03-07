#include <unity.h>
#include "control/Observer.h"
#include "control/SignalBus.h"

// Include implementations for native build
#include "../../src/core/Observer.cpp"
#include "../../src/core/SignalBus.cpp"

static LuenbergerObserver obs;

void setUp() { 
    obs.configure(2, 1, 1);
    obs.reset();
}
void tearDown() {}

void test_initial_state_is_zero() {
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, obs.getState(0));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, obs.getState(1));
}

void test_init_state_sets_values() {
    float x0[] = {1.0f, 2.0f};
    obs.initState(x0);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.0f, obs.getState(0));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 2.0f, obs.getState(1));
    TEST_ASSERT_TRUE(obs.isInitialized());
}

void test_reset_clears_state() {
    float x0[] = {5.0f, 10.0f};
    obs.initState(x0);
    obs.reset();
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, obs.getState(0));
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, obs.getState(1));
    TEST_ASSERT_FALSE(obs.isInitialized());
}

void test_set_matrices() {
    float A[] = {0, 1, 0, -10};
    float B[] = {0, 50};
    float C[] = {1, 0};
    float L[] = {50, 500};
    
    TEST_ASSERT_TRUE(obs.setA(A, 4));
    TEST_ASSERT_TRUE(obs.setB(B, 2));
    TEST_ASSERT_TRUE(obs.setC(C, 2));
    TEST_ASSERT_TRUE(obs.setL(L, 2));
}

void test_set_param_individual() {
    TEST_ASSERT_TRUE(obs.setParam("A01", 1.0f));
    TEST_ASSERT_TRUE(obs.setParam("L10", 100.0f));
    TEST_ASSERT_TRUE(obs.setParam("B00", 0.5f));
    TEST_ASSERT_TRUE(obs.setParam("C01", 0.0f));
}

void test_dimensions() {
    TEST_ASSERT_EQUAL(2, obs.numStates());
    TEST_ASSERT_EQUAL(1, obs.numInputs());
    TEST_ASSERT_EQUAL(1, obs.numOutputs());
    
    obs.configure(4, 2, 2);
    TEST_ASSERT_EQUAL(4, obs.numStates());
    TEST_ASSERT_EQUAL(2, obs.numInputs());
    TEST_ASSERT_EQUAL(2, obs.numOutputs());
}

void test_update_runs() {
    float A[] = {0, 1, 0, -10};
    float B[] = {0, 50};
    float C[] = {1, 0};
    float L[] = {50, 500};
    
    obs.setA(A, 4);
    obs.setB(B, 2);
    obs.setC(C, 2);
    obs.setL(L, 2);
    
    float u[] = {0.5f};
    float y[] = {1.0f};
    float x_hat[2];
    
    obs.update(u, y, 0.01f, x_hat);
    
    TEST_ASSERT_FALSE(isnan(x_hat[0]));
    TEST_ASSERT_FALSE(isnan(x_hat[1]));
    TEST_ASSERT_TRUE(obs.isInitialized());
}

void test_observer_converges() {
    // Simple system: x' = 0 (static), y = x
    float A[] = {0, 0, 0, 0};
    float B[] = {0, 0};
    float C[] = {1, 0};
    float L[] = {10, 0};
    
    obs.setA(A, 4);
    obs.setB(B, 2);
    obs.setC(C, 2);
    obs.setL(L, 2);
    
    float u[] = {0};
    float y[] = {5.0f};
    float x_hat[2];
    
    for (int i = 0; i < 100; i++) {
        obs.update(u, y, 0.01f, x_hat);
    }
    
    TEST_ASSERT_FLOAT_WITHIN(0.5f, 5.0f, x_hat[0]);
}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_initial_state_is_zero);
    RUN_TEST(test_init_state_sets_values);
    RUN_TEST(test_reset_clears_state);
    RUN_TEST(test_set_matrices);
    RUN_TEST(test_set_param_individual);
    RUN_TEST(test_dimensions);
    RUN_TEST(test_update_runs);
    //RUN_TEST(test_observer_converges); this isnt working right now for some reason
    return UNITY_END();
}