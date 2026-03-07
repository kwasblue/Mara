// test/test_golden_path/test_golden_path.cpp
// Golden path integration test - verifies the intent-based command pipeline:
// Command → IntentBuffer → Control Loop Consumption
//
// This test focuses on the decoupled command/actuation boundary.

#include <unity.h>
#include <string>
#include <ArduinoJson.h>

// Core dependencies
#include "core/IntentBuffer.h"

// Include implementations for native build
#include "../../src/core/IntentBuffer.cpp"

// =============================================================================
// Test Fixtures
// =============================================================================

static mara::IntentBuffer* pIntents = nullptr;

void setUp() {
    if (!pIntents) {
        pIntents = new mara::IntentBuffer();
    }
}

void tearDown() {
    // Clear intents between tests
    if (pIntents) {
        pIntents->clearAll();
    }
}

// =============================================================================
// Intent Buffer Tests (Core of the Golden Path)
// =============================================================================

// Test 1: Velocity intent flow - set and consume
void test_velocity_intent_set_and_consume() {
    // Simulate command handler setting velocity intent
    pIntents->setVelocityIntent(0.5f, 0.3f, 1000);

    // Simulate control loop consuming intent
    mara::VelocityIntent intent;
    bool consumed = pIntents->consumeVelocityIntent(intent);

    TEST_ASSERT_TRUE(consumed);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.5f, intent.vx);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.3f, intent.omega);
    TEST_ASSERT_EQUAL_UINT32(1000, intent.timestamp_ms);

    // Second consume should return false (already consumed)
    bool secondConsume = pIntents->consumeVelocityIntent(intent);
    TEST_ASSERT_FALSE(secondConsume);
}

// Test 2: Latest-wins semantics - multiple sets before consume
void test_velocity_intent_latest_wins() {
    // Multiple velocity commands in rapid succession
    pIntents->setVelocityIntent(0.1f, 0.1f, 100);
    pIntents->setVelocityIntent(0.2f, 0.2f, 200);
    pIntents->setVelocityIntent(0.3f, 0.3f, 300);  // This should win

    // Control loop consumes only the latest
    mara::VelocityIntent intent;
    bool consumed = pIntents->consumeVelocityIntent(intent);

    TEST_ASSERT_TRUE(consumed);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.3f, intent.vx);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.3f, intent.omega);
    TEST_ASSERT_EQUAL_UINT32(300, intent.timestamp_ms);
}

// Test 3: Servo intent flow
void test_servo_intent_set_and_consume() {
    // Set servo intent
    pIntents->setServoIntent(0, 90.0f, 500, 1000);

    // Consume
    mara::ServoIntent intent;
    bool consumed = pIntents->consumeServoIntent(0, intent);

    TEST_ASSERT_TRUE(consumed);
    TEST_ASSERT_EQUAL_UINT8(0, intent.id);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 90.0f, intent.angle_deg);
    TEST_ASSERT_EQUAL_UINT32(500, intent.duration_ms);
}

// Test 4: DC Motor intent flow
void test_dc_motor_intent_set_and_consume() {
    // Set DC motor intent
    pIntents->setDcMotorIntent(1, 0.75f, 1000);

    // Consume
    mara::DcMotorIntent intent;
    bool consumed = pIntents->consumeDcMotorIntent(1, intent);

    TEST_ASSERT_TRUE(consumed);
    TEST_ASSERT_EQUAL_UINT8(1, intent.id);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.75f, intent.speed);
}

// Test 5: Stepper intent flow
void test_stepper_intent_set_and_consume() {
    // Set stepper intent
    pIntents->setStepperIntent(0, 200, 100.0f, 1000);

    // Consume
    mara::StepperIntent intent;
    bool consumed = pIntents->consumeStepperIntent(0, intent);

    TEST_ASSERT_TRUE(consumed);
    TEST_ASSERT_EQUAL_INT(0, intent.motor_id);
    TEST_ASSERT_EQUAL_INT(200, intent.steps);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 100.0f, intent.speed_steps_s);
}

// Test 6: Signal intent queue (ring buffer)
void test_signal_intent_queue() {
    // Queue multiple signal intents
    pIntents->queueSignalIntent(1, 1.0f, 100);
    pIntents->queueSignalIntent(2, 2.0f, 200);
    pIntents->queueSignalIntent(3, 3.0f, 300);

    TEST_ASSERT_EQUAL_UINT8(3, pIntents->pendingSignalCount());

    // Consume in FIFO order
    mara::SignalIntent intent;

    bool c1 = pIntents->consumeSignalIntent(intent);
    TEST_ASSERT_TRUE(c1);
    TEST_ASSERT_EQUAL_UINT16(1, intent.id);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 1.0f, intent.value);

    bool c2 = pIntents->consumeSignalIntent(intent);
    TEST_ASSERT_TRUE(c2);
    TEST_ASSERT_EQUAL_UINT16(2, intent.id);

    bool c3 = pIntents->consumeSignalIntent(intent);
    TEST_ASSERT_TRUE(c3);
    TEST_ASSERT_EQUAL_UINT16(3, intent.id);

    // Queue empty
    bool c4 = pIntents->consumeSignalIntent(intent);
    TEST_ASSERT_FALSE(c4);
}

// Test 7: Clear all intents (E-stop scenario)
void test_clear_all_intents() {
    // Set various intents
    pIntents->setVelocityIntent(1.0f, 1.0f, 100);
    pIntents->setServoIntent(0, 45.0f, 0, 100);
    pIntents->setDcMotorIntent(0, 0.5f, 100);
    pIntents->queueSignalIntent(1, 1.0f, 100);

    // Clear all (E-stop)
    pIntents->clearAll();

    // All should be empty
    mara::VelocityIntent vel;
    TEST_ASSERT_FALSE(pIntents->consumeVelocityIntent(vel));

    mara::ServoIntent servo;
    TEST_ASSERT_FALSE(pIntents->consumeServoIntent(0, servo));

    mara::DcMotorIntent dc;
    TEST_ASSERT_FALSE(pIntents->consumeDcMotorIntent(0, dc));

    TEST_ASSERT_EQUAL_UINT8(0, pIntents->pendingSignalCount());
}

// Test 8: Independent motor IDs
void test_independent_motor_ids() {
    // Set intents for different motor IDs
    pIntents->setDcMotorIntent(0, 0.5f, 100);
    pIntents->setDcMotorIntent(1, -0.5f, 100);
    pIntents->setDcMotorIntent(2, 0.25f, 100);

    // Consume each independently
    mara::DcMotorIntent intent0, intent1, intent2;

    TEST_ASSERT_TRUE(pIntents->consumeDcMotorIntent(0, intent0));
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.5f, intent0.speed);

    TEST_ASSERT_TRUE(pIntents->consumeDcMotorIntent(1, intent1));
    TEST_ASSERT_FLOAT_WITHIN(0.01f, -0.5f, intent1.speed);

    TEST_ASSERT_TRUE(pIntents->consumeDcMotorIntent(2, intent2));
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.25f, intent2.speed);
}

// =============================================================================
// Test Runner
// =============================================================================

int main(int argc, char** argv) {
    (void)argc;
    (void)argv;

    UNITY_BEGIN();

    RUN_TEST(test_velocity_intent_set_and_consume);
    RUN_TEST(test_velocity_intent_latest_wins);
    RUN_TEST(test_servo_intent_set_and_consume);
    RUN_TEST(test_dc_motor_intent_set_and_consume);
    RUN_TEST(test_stepper_intent_set_and_consume);
    RUN_TEST(test_signal_intent_queue);
    RUN_TEST(test_clear_all_intents);
    RUN_TEST(test_independent_motor_ids);

    // Cleanup
    delete pIntents;
    pIntents = nullptr;

    return UNITY_END();
}
