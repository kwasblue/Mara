// test/test_safety/test_safety.cpp

#include <unity.h>
#include <cmath>
#include <math.h> 


// -----------------------------------------------------------------------------
// Minimal ModeManager logic for testing (no hardware dependencies)
// This mirrors the core logic from src/core/ModeManager.cpp
// -----------------------------------------------------------------------------

enum class MaraMode : uint8_t {
    BOOT,
    DISCONNECTED,
    IDLE,
    ARMED,
    ACTIVE,
    ESTOPPED
};

struct SafetyConfig {
    uint32_t host_timeout_ms = 500;
    uint32_t motion_timeout_ms = 500;
    float max_linear_vel = 2.0f;
    float max_angular_vel = 3.14f;
};

class TestModeManager {
public:
    using StopCallback = void (*)();
    
    void configure(const SafetyConfig& cfg) { cfg_ = cfg; }
    
    void update(uint32_t now_ms) {
        // Host timeout
        if (hostEverSeen_ && isConnected() && !isEstopped()) {
            if (now_ms - lastHostHeartbeat_ > cfg_.host_timeout_ms) {
                triggerStop();
                mode_ = MaraMode::DISCONNECTED;
            }
        }
        
        // Motion timeout (only in ACTIVE)
        if (mode_ == MaraMode::ACTIVE && lastMotionCmd_ > 0) {
            if (now_ms - lastMotionCmd_ > cfg_.motion_timeout_ms) {
                triggerStop();
            }
        }
    }
    
    void onHostHeartbeat(uint32_t now_ms) {
        lastHostHeartbeat_ = now_ms;
        if (!hostEverSeen_) {
            hostEverSeen_ = true;
        }
        if (mode_ == MaraMode::DISCONNECTED) {
            mode_ = MaraMode::IDLE;
        }
    }
    
    void onMotionCommand(uint32_t now_ms) {
        lastMotionCmd_ = now_ms;
    }
    
    void arm() {
        if (mode_ == MaraMode::IDLE) {
            mode_ = MaraMode::ARMED;
        }
    }
    
    void activate() {
        if (mode_ == MaraMode::ARMED) {
            mode_ = MaraMode::ACTIVE;
        }
    }
    
    void deactivate() {
        if (mode_ == MaraMode::ACTIVE) {
            triggerStop();
            mode_ = MaraMode::ARMED;
        }
    }
    
    void disarm() {
        if (mode_ == MaraMode::ARMED || mode_ == MaraMode::ACTIVE) {
            triggerStop();
            mode_ = MaraMode::IDLE;
        }
    }
    
    void estop() {
        triggerStop();
        mode_ = MaraMode::ESTOPPED;
    }
    
    bool clearEstop() {
        if (!isEstopped()) return true;
        mode_ = MaraMode::IDLE;
        return true;
    }
    
    bool validateVelocity(float vx, float omega, float& out_vx, float& out_omega) {
        if (isnan(vx) || isinf(vx) || isnan(omega) || isinf(omega)) {
            out_vx = 0;
            out_omega = 0;
            return false;
        }
            
        out_vx = vx;
        if (out_vx > cfg_.max_linear_vel) out_vx = cfg_.max_linear_vel;
        if (out_vx < -cfg_.max_linear_vel) out_vx = -cfg_.max_linear_vel;
        
        out_omega = omega;
        if (out_omega > cfg_.max_angular_vel) out_omega = cfg_.max_angular_vel;
        if (out_omega < -cfg_.max_angular_vel) out_omega = -cfg_.max_angular_vel;
        
        return true;
    }
    
    MaraMode mode() const { return mode_; }
    bool canMove() const { return mode_ == MaraMode::ARMED || mode_ == MaraMode::ACTIVE; }
    bool isEstopped() const { return mode_ == MaraMode::ESTOPPED; }
    bool isConnected() const { return mode_ != MaraMode::BOOT && mode_ != MaraMode::DISCONNECTED; }
    
    void onStop(StopCallback cb) { stopCallback_ = cb; }
    int stopCount() const { return stopCount_; }
    
private:
    SafetyConfig cfg_;
    MaraMode mode_ = MaraMode::DISCONNECTED;
    uint32_t lastHostHeartbeat_ = 0;
    uint32_t lastMotionCmd_ = 0;
    bool hostEverSeen_ = false;
    StopCallback stopCallback_ = nullptr;
    int stopCount_ = 0;
    
    void triggerStop() {
        stopCount_++;
        if (stopCallback_) stopCallback_();
    }
};

// -----------------------------------------------------------------------------
// Test fixtures
// -----------------------------------------------------------------------------

static TestModeManager* g_mode = nullptr;
static bool g_stopCalled = false;

void stopCallback() { g_stopCalled = true; }

void setUp() {
    g_mode = new TestModeManager();
    g_stopCalled = false;
    
    SafetyConfig cfg;
    cfg.host_timeout_ms = 500;
    cfg.motion_timeout_ms = 500;
    cfg.max_linear_vel = 2.0f;
    cfg.max_angular_vel = 3.14f;
    
    g_mode->configure(cfg);
    g_mode->onStop(stopCallback);
}

void tearDown() {
    delete g_mode;
    g_mode = nullptr;
}

// -----------------------------------------------------------------------------
// Host Timeout Tests
// -----------------------------------------------------------------------------

void test_host_timeout_triggers_stop() {
    g_mode->onHostHeartbeat(0);
    TEST_ASSERT_EQUAL(MaraMode::IDLE, g_mode->mode());
    
    g_mode->update(600);
    
    TEST_ASSERT_TRUE(g_stopCalled);
    TEST_ASSERT_EQUAL(MaraMode::DISCONNECTED, g_mode->mode());
}

void test_heartbeat_prevents_timeout() {
    g_mode->onHostHeartbeat(0);
    g_mode->update(400);
    g_mode->onHostHeartbeat(400);
    g_mode->update(800);
    
    TEST_ASSERT_FALSE(g_stopCalled);
    TEST_ASSERT_EQUAL(MaraMode::IDLE, g_mode->mode());
}

void test_no_timeout_before_first_heartbeat() {
    g_mode->update(2000);
    
    TEST_ASSERT_FALSE(g_stopCalled);
    TEST_ASSERT_EQUAL(MaraMode::DISCONNECTED, g_mode->mode());
}

// -----------------------------------------------------------------------------
// Motion Timeout Tests
// -----------------------------------------------------------------------------

void test_motion_timeout_triggers_stop() {
    g_mode->onHostHeartbeat(0);
    g_mode->arm();
    g_mode->activate();
    g_mode->onMotionCommand(100);
    
    g_mode->onHostHeartbeat(200);
    g_mode->onHostHeartbeat(400);
    g_mode->update(700);
    
    TEST_ASSERT_TRUE(g_stopCalled);
    TEST_ASSERT_EQUAL(MaraMode::ACTIVE, g_mode->mode());
}

void test_motion_commands_prevent_timeout() {
    g_mode->onHostHeartbeat(0);
    g_mode->arm();
    g_mode->activate();
    
    g_mode->onMotionCommand(100);
    g_mode->onHostHeartbeat(200);
    g_mode->onMotionCommand(300);
    g_mode->update(400);
    
    TEST_ASSERT_FALSE(g_stopCalled);
}

void test_motion_timeout_only_in_active() {
    g_mode->onHostHeartbeat(0);
    g_mode->arm();  // ARMED, not ACTIVE
    
    g_mode->onMotionCommand(100);
    g_mode->onHostHeartbeat(200);
    g_mode->onHostHeartbeat(400);
    g_mode->update(700);
    
    TEST_ASSERT_FALSE(g_stopCalled);
}

// -----------------------------------------------------------------------------
// State Transition Tests
// -----------------------------------------------------------------------------

void test_arm_from_idle() {
    g_mode->onHostHeartbeat(0);
    g_mode->arm();
    TEST_ASSERT_EQUAL(MaraMode::ARMED, g_mode->mode());
}

void test_arm_from_disconnected_fails() {
    g_mode->arm();
    TEST_ASSERT_EQUAL(MaraMode::DISCONNECTED, g_mode->mode());
}

void test_activate_from_armed() {
    g_mode->onHostHeartbeat(0);
    g_mode->arm();
    g_mode->activate();
    TEST_ASSERT_EQUAL(MaraMode::ACTIVE, g_mode->mode());
}

void test_activate_from_idle_fails() {
    g_mode->onHostHeartbeat(0);
    g_mode->activate();
    TEST_ASSERT_EQUAL(MaraMode::IDLE, g_mode->mode());
}

void test_deactivate_triggers_stop() {
    g_mode->onHostHeartbeat(0);
    g_mode->arm();
    g_mode->activate();
    g_mode->deactivate();
    
    TEST_ASSERT_TRUE(g_stopCalled);
    TEST_ASSERT_EQUAL(MaraMode::ARMED, g_mode->mode());
}

void test_disarm_from_active_triggers_stop() {
    g_mode->onHostHeartbeat(0);
    g_mode->arm();
    g_mode->activate();
    g_mode->disarm();
    
    TEST_ASSERT_TRUE(g_stopCalled);
    TEST_ASSERT_EQUAL(MaraMode::IDLE, g_mode->mode());
}

// -----------------------------------------------------------------------------
// E-stop Tests
// -----------------------------------------------------------------------------

void test_estop_from_active() {
    g_mode->onHostHeartbeat(0);
    g_mode->arm();
    g_mode->activate();
    g_mode->estop();
    
    TEST_ASSERT_TRUE(g_stopCalled);
    TEST_ASSERT_EQUAL(MaraMode::ESTOPPED, g_mode->mode());
}

void test_estop_blocks_arm() {
    g_mode->onHostHeartbeat(0);
    g_mode->estop();
    g_mode->arm();
    
    TEST_ASSERT_EQUAL(MaraMode::ESTOPPED, g_mode->mode());
}

void test_clear_estop_returns_to_idle() {
    g_mode->onHostHeartbeat(0);
    g_mode->estop();
    g_mode->clearEstop();
    
    TEST_ASSERT_EQUAL(MaraMode::IDLE, g_mode->mode());
}

void test_can_move_states() {
    g_mode->onHostHeartbeat(0);
    TEST_ASSERT_FALSE(g_mode->canMove());
    
    g_mode->arm();
    TEST_ASSERT_TRUE(g_mode->canMove());
    
    g_mode->activate();
    TEST_ASSERT_TRUE(g_mode->canMove());
    
    g_mode->estop();
    TEST_ASSERT_FALSE(g_mode->canMove());
}

// -----------------------------------------------------------------------------
// Velocity Validation Tests
// -----------------------------------------------------------------------------

void test_nan_velocity_rejected() {
    float out_vx, out_omega;
    bool valid = g_mode->validateVelocity(NAN, 0.0f, out_vx, out_omega);
    
    TEST_ASSERT_FALSE(valid);
    TEST_ASSERT_EQUAL_FLOAT(0.0f, out_vx);
}

void test_inf_velocity_rejected() {
    float out_vx, out_omega;
    bool valid = g_mode->validateVelocity(INFINITY, 0.0f, out_vx, out_omega);
    
    TEST_ASSERT_FALSE(valid);
}

void test_velocity_clamping() {
    float out_vx, out_omega;
    bool valid = g_mode->validateVelocity(10.0f, 10.0f, out_vx, out_omega);
    
    TEST_ASSERT_TRUE(valid);
    TEST_ASSERT_EQUAL_FLOAT(2.0f, out_vx);
    TEST_ASSERT_EQUAL_FLOAT(3.14f, out_omega);
}

void test_valid_velocity_passes() {
    float out_vx, out_omega;
    bool valid = g_mode->validateVelocity(1.0f, 1.0f, out_vx, out_omega);
    
    TEST_ASSERT_TRUE(valid);
    TEST_ASSERT_EQUAL_FLOAT(1.0f, out_vx);
    TEST_ASSERT_EQUAL_FLOAT(1.0f, out_omega);
}

// -----------------------------------------------------------------------------
// Cross-platform test runner
// -----------------------------------------------------------------------------

#include "../test_runner.h"

void run_tests() {
    // Host timeout
    RUN_TEST(test_host_timeout_triggers_stop);
    RUN_TEST(test_heartbeat_prevents_timeout);
    RUN_TEST(test_no_timeout_before_first_heartbeat);

    // Motion timeout
    RUN_TEST(test_motion_timeout_triggers_stop);
    RUN_TEST(test_motion_commands_prevent_timeout);
    RUN_TEST(test_motion_timeout_only_in_active);

    // State transitions
    RUN_TEST(test_arm_from_idle);
    RUN_TEST(test_arm_from_disconnected_fails);
    RUN_TEST(test_activate_from_armed);
    RUN_TEST(test_activate_from_idle_fails);
    RUN_TEST(test_deactivate_triggers_stop);
    RUN_TEST(test_disarm_from_active_triggers_stop);

    // E-stop
    RUN_TEST(test_estop_from_active);
    RUN_TEST(test_estop_blocks_arm);
    RUN_TEST(test_clear_estop_returns_to_idle);
    RUN_TEST(test_can_move_states);

    // Velocity validation
    RUN_TEST(test_nan_velocity_rejected);
    RUN_TEST(test_inf_velocity_rejected);
    RUN_TEST(test_velocity_clamping);
    RUN_TEST(test_valid_velocity_passes);
}

TEST_RUNNER(run_tests)