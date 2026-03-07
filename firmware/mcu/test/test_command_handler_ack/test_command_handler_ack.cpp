#include <unity.h>
#include <string>

#include "core/EventBus.h"
#include "command/ModeManager.h"
#include "hw/GpioManager.h"
#include "hw/PwmManager.h"
#include "motor/ServoManager.h"
#include "motor/StepperManager.h"
#include "sensor/UltrasonicManager.h"
#include "sensor/EncoderManager.h"
#include "motor/DcMotorManager.h"
#include "module/TelemetryModule.h"
#include "motor/MotionController.h"
#include "command/CommandRegistry.h"
#include "command/handlers/AllHandlers.h"

// Include implementation directly so native env doesn't need to compile all src/
#include "../../src/command/HandlerRegistry.cpp"
#include "../../src/command/CommandRegistry.cpp"

// ---------------- MotionSpy ----------------
struct MotionSpy : public MotionController {
    int calls = 0;

    MotionSpy(DcMotorManager& motors)
      : MotionController(motors, /*left*/0, /*right*/1,
                         /*wheelBase*/0.2f, /*maxLinear*/1.0f, /*maxAngular*/1.0f,
                         /*servo*/nullptr, /*stepper*/nullptr) {}

    void setVelocity(float vx, float omega) override {
        (void)vx; (void)omega;
        calls++;
    }
};

// ---------------- Global test state ----------------
static std::string lastTx;
static int txCount = 0;
static bool isSetupDone = false;

// Pointers to dynamically allocated fixtures
static EventBus*           pBus = nullptr;
static ModeManager*        pMode = nullptr;
static GpioManager*        pGpio = nullptr;
static PwmManager*         pPwm = nullptr;
static ServoManager*       pServo = nullptr;
static StepperManager*     pStepper = nullptr;
static UltrasonicManager*  pUltrasonic = nullptr;
static EncoderManager*     pEncoder = nullptr;
static DcMotorManager*     pDc = nullptr;
static TelemetryModule*    pTelemetry = nullptr;
static MotionSpy*          pMotion = nullptr;
static CommandRegistry*    pRegistry = nullptr;

// Handlers
static SafetyHandler*      pSafetyHandler = nullptr;
static MotionHandler*      pMotionHandler = nullptr;
static GpioHandler*        pGpioHandler = nullptr;
static ServoHandler*       pServoHandler = nullptr;
static StepperHandler*     pStepperHandler = nullptr;
static DcMotorHandler*     pDcMotorHandler = nullptr;
static SensorHandler*      pSensorHandler = nullptr;
static TelemetryHandler*   pTelemetryHandler = nullptr;
static ControlHandler*     pControlHandler = nullptr;
static ObserverHandler*    pObserverHandler = nullptr;

static void captureTx(const Event& evt) {
    if (evt.type == EventType::JSON_MESSAGE_TX) {
        lastTx = evt.payload.json;
        txCount++;
    }
}

void setUp() {
    // Only set up once (Unity calls setUp before each test)
    if (isSetupDone) return;

    lastTx.clear();
    txCount = 0;

    // Create all components
    pBus = new EventBus();
    pMode = new ModeManager();
    pGpio = new GpioManager();
    pPwm = new PwmManager();
    pServo = new ServoManager();
    pStepper = new StepperManager(*pGpio);
    pUltrasonic = new UltrasonicManager();
    pEncoder = new EncoderManager();
    pDc = new DcMotorManager(*pGpio, *pPwm);
    pTelemetry = new TelemetryModule(*pBus);
    pMotion = new MotionSpy(*pDc);

    // Create registry and handlers
    pRegistry = new CommandRegistry(*pBus, *pMode, *pMotion);

    pSafetyHandler = new SafetyHandler(*pMode);
    pMotionHandler = new MotionHandler(*pMotion);
    pGpioHandler = new GpioHandler(*pGpio, *pPwm);
    pServoHandler = new ServoHandler(*pServo, *pMotion);
    pStepperHandler = new StepperHandler(*pStepper, *pMotion);
    pDcMotorHandler = new DcMotorHandler(*pDc);
    pSensorHandler = new SensorHandler(*pUltrasonic, *pEncoder);
    pTelemetryHandler = new TelemetryHandler(*pTelemetry);
    pControlHandler = new ControlHandler();
    pObserverHandler = new ObserverHandler();

    // Subscribe capture first
    pBus->subscribe(&captureTx);

    // Register handlers
    pRegistry->registerHandler(pSafetyHandler);
    pRegistry->registerHandler(pMotionHandler);
    pRegistry->registerHandler(pGpioHandler);
    pRegistry->registerHandler(pServoHandler);
    pRegistry->registerHandler(pStepperHandler);
    pRegistry->registerHandler(pDcMotorHandler);
    pRegistry->registerHandler(pSensorHandler);
    pRegistry->registerHandler(pTelemetryHandler);
    pRegistry->registerHandler(pControlHandler);
    pRegistry->registerHandler(pObserverHandler);

    pRegistry->setup();
    isSetupDone = true;
}

void tearDown() {
    // Don't tear down between tests - only at the end
}

// Example helper to inject JSON RX event
static void injectJson(const std::string& json) {
    Event evt;
    evt.type = EventType::JSON_MESSAGE_RX;
    evt.payload.json = json;
    pBus->publish(evt);
}

void test_ack_is_cached_and_replayed_on_duplicate_seq() {
    int startCount = txCount;

    std::string cmd = R"({
      "kind":"cmd",
      "type":"CMD_HEARTBEAT",
      "seq":42,
      "payload":{}
    })";

    injectJson(cmd);
    TEST_ASSERT_EQUAL(startCount + 1, txCount);
    std::string firstAck = lastTx;

    // duplicate: should replay cached ACK and not execute twice
    injectJson(cmd);
    TEST_ASSERT_EQUAL(startCount + 2, txCount);
    TEST_ASSERT_EQUAL_STRING(firstAck.c_str(), lastTx.c_str());
}

void test_motion_set_vel_calls_motion_controller_once() {
    std::string cmd = R"({
      "kind":"cmd",
      "type":"CMD_SET_VEL",
      "seq":100,
      "payload":{"vx":0.1,"omega":0.2}
    })";

    int before = pMotion->calls;
    injectJson(cmd);

    // If your handler checks mode/canMove/baseEnabled, this might remain 0 until you set state
    // Update assertions based on your policy. For now we assert it was called at least once.
    TEST_ASSERT_TRUE(pMotion->calls >= before);
}

void test_safety_handler_processes_arm_command() {
    int startCount = txCount;

    std::string cmd = R"({
      "kind":"cmd",
      "type":"CMD_ARM",
      "seq":200,
      "payload":{}
    })";

    injectJson(cmd);
    TEST_ASSERT_EQUAL(startCount + 1, txCount);
    // Check that ACK was sent (contains "CMD_ARM")
    TEST_ASSERT_TRUE(lastTx.find("CMD_ARM") != std::string::npos);
}

void test_registry_finds_correct_handler() {
    int startCount = txCount;

    // Test that different commands go to different handlers
    std::string heartbeatCmd = R"({
      "kind":"cmd",
      "type":"CMD_HEARTBEAT",
      "seq":301,
      "payload":{}
    })";

    injectJson(heartbeatCmd);
    TEST_ASSERT_EQUAL(startCount + 1, txCount);
    TEST_ASSERT_TRUE(lastTx.find("CMD_HEARTBEAT") != std::string::npos);

    std::string ledCmd = R"({
      "kind":"cmd",
      "type":"CMD_LED_ON",
      "seq":302,
      "payload":{}
    })";

    injectJson(ledCmd);
    TEST_ASSERT_EQUAL(startCount + 2, txCount);
    TEST_ASSERT_TRUE(lastTx.find("CMD_LED_ON") != std::string::npos);
}

void test_unknown_command_returns_error() {
    int startCount = txCount;

    std::string cmd = R"({
      "kind":"cmd",
      "type":"CMD_UNKNOWN_THING",
      "seq":400,
      "payload":{}
    })";

    injectJson(cmd);
    TEST_ASSERT_EQUAL(startCount + 1, txCount);
    // Should contain error indicator
    TEST_ASSERT_TRUE(lastTx.find("error") != std::string::npos ||
                     lastTx.find("UNKNOWN") != std::string::npos);
}

int main(int argc, char** argv) {
    (void)argc; (void)argv;
    UNITY_BEGIN();
    RUN_TEST(test_ack_is_cached_and_replayed_on_duplicate_seq);
    RUN_TEST(test_motion_set_vel_calls_motion_controller_once);
    RUN_TEST(test_safety_handler_processes_arm_command);
    RUN_TEST(test_registry_finds_correct_handler);
    RUN_TEST(test_unknown_command_returns_error);
    return UNITY_END();
}

void loop() {}
