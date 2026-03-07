#include <unity.h>
#include "control/ControlKernel.h"
#include "control/SignalBus.h"

// Include implementations for native build
#include "../../src/core/ControlKernel.cpp"
#include "../../src/core/SignalBus.cpp"

static ControlKernel kernel;
static SignalBus bus;

void setUp() { 
    kernel.resetAll();
    bus.clear();
}
void tearDown() {}

void test_configure_pid_slot() {
    SlotConfig cfg;
    cfg.slot = 0;
    cfg.rate_hz = 100;
    cfg.io.ref_id = 100;
    cfg.io.meas_id = 101;
    cfg.io.out_id = 102;
    cfg.require_armed = true;
    cfg.require_active = true;
    
    TEST_ASSERT_TRUE(kernel.configureSlot(cfg, "PID"));
    
    auto config = kernel.getConfig(0);
    TEST_ASSERT_EQUAL(100, config.rate_hz);
}

void test_enable_disable_slot() {
    SlotConfig cfg;
    cfg.slot = 0;
    cfg.rate_hz = 100;
    cfg.io.ref_id = 100;
    cfg.io.meas_id = 101;
    cfg.io.out_id = 102;
    
    kernel.configureSlot(cfg, "PID");
    
    TEST_ASSERT_TRUE(kernel.enableSlot(0, true));
    auto config = kernel.getConfig(0);
    TEST_ASSERT_TRUE(config.enabled);
    
    TEST_ASSERT_TRUE(kernel.enableSlot(0, false));
    config = kernel.getConfig(0);
    TEST_ASSERT_FALSE(config.enabled);
}

void test_set_pid_gains() {
    SlotConfig cfg;
    cfg.slot = 0;
    cfg.rate_hz = 100;
    cfg.io.ref_id = 100;
    cfg.io.meas_id = 101;
    cfg.io.out_id = 102;
    
    kernel.configureSlot(cfg, "PID");
    
    TEST_ASSERT_TRUE(kernel.setParam(0, "kp", 1.5f));
    TEST_ASSERT_TRUE(kernel.setParam(0, "ki", 0.5f));
    TEST_ASSERT_TRUE(kernel.setParam(0, "kd", 0.1f));
}

void test_reset_slot() {
    SlotConfig cfg;
    cfg.slot = 0;
    cfg.rate_hz = 100;
    cfg.io.ref_id = 100;
    cfg.io.meas_id = 101;
    cfg.io.out_id = 102;
    
    kernel.configureSlot(cfg, "PID");
    kernel.enableSlot(0, true);
    
    TEST_ASSERT_TRUE(kernel.resetSlot(0));
}

void test_configure_state_space_slot() {
    SlotConfig cfg;
    cfg.slot = 0;
    cfg.rate_hz = 200;
    cfg.ss_io.num_states = 2;
    cfg.ss_io.num_inputs = 1;
    cfg.ss_io.state_ids[0] = 100;
    cfg.ss_io.state_ids[1] = 101;
    cfg.ss_io.ref_ids[0] = 200;
    cfg.ss_io.ref_ids[1] = 201;
    cfg.ss_io.output_ids[0] = 300;
    
    TEST_ASSERT_TRUE(kernel.configureSlot(cfg, "STATE_SPACE"));
}

void test_set_state_space_gains() {
    SlotConfig cfg;
    cfg.slot = 0;
    cfg.rate_hz = 200;
    cfg.ss_io.num_states = 2;
    cfg.ss_io.num_inputs = 1;
    
    kernel.configureSlot(cfg, "STATE_SPACE");
    
    float K[] = {1.0f, 0.5f};
    TEST_ASSERT_TRUE(kernel.setParamArray(0, "K", K, 2));
}

void test_disable_all() {
    SlotConfig cfg;
    cfg.slot = 0;
    cfg.rate_hz = 100;
    cfg.io.ref_id = 100;
    cfg.io.meas_id = 101;
    cfg.io.out_id = 102;
    
    kernel.configureSlot(cfg, "PID");
    kernel.enableSlot(0, true);
    
    kernel.disableAll();
    
    auto config = kernel.getConfig(0);
    TEST_ASSERT_FALSE(config.enabled);
}

void test_step_with_signals() {
    // Setup signals
    bus.define(100, "ref", SignalBus::Kind::REF, 5.0f);
    bus.define(101, "meas", SignalBus::Kind::MEAS, 0.0f);
    bus.define(102, "out", SignalBus::Kind::OUT, 0.0f);
    
    // Configure PID
    SlotConfig cfg;
    cfg.slot = 0;
    cfg.rate_hz = 100;
    cfg.io.ref_id = 100;
    cfg.io.meas_id = 101;
    cfg.io.out_id = 102;
    
    kernel.configureSlot(cfg, "PID");
    kernel.setParam(0, "kp", 1.0f);
    kernel.enableSlot(0, true);
    
    // Step - should compute output
    kernel.step(1000, 0.01f, bus, true, true);
    
    // Output should be non-zero (error = 5, kp = 1 -> output = 5, clamped to 1)
    float out_val;
    bus.get(102, out_val);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 1.0f, out_val);  // Clamped to default limit
}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_configure_pid_slot);
    RUN_TEST(test_enable_disable_slot);
    RUN_TEST(test_set_pid_gains);
    RUN_TEST(test_reset_slot);
    RUN_TEST(test_configure_state_space_slot);
    RUN_TEST(test_set_state_space_gains);
    RUN_TEST(test_disable_all);
    RUN_TEST(test_step_with_signals);
    return UNITY_END();
}