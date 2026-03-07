// test/test_identity_version_handshake/test_identity_version_handshake.cpp

#include <unity.h>
#include <string>

#include "core/EventBus.h"
#include "core/Event.h"

// Include the module header so we can construct it
#include "module/IdentityModule.h"
#include "transport/MultiTransport.h"

// Pull in the implementation directly for native tests (since test_build_src=false)
#include "../../src/core/LoopRates.cpp"
#include "../../src/config/DeviceManifest.cpp"
#include "../../src/module/IdentityModule.cpp"

static EventBus bus;

// IdentityModule ctor requires a MultiTransport + name, even if not used yet
static MultiTransport multi;
static IdentityModule identity(bus, multi, "robot");

// Capture JSON_MESSAGE_TX events
static std::string lastTx;
static int txCount = 0;

static void captureTx(const Event& evt) {
    if (evt.type == EventType::JSON_MESSAGE_TX) {
        lastTx = evt.payload.json;
        txCount++;
    }
}

void setUp() {
    lastTx.clear();
    txCount = 0;

    // subscribe capture first so we see identity output
    bus.subscribe(&captureTx);

    // normal module setup
    identity.setup();
}

void tearDown() {}

void test_identity_emits_handshake_on_whoami_request() {
    // Publish the trigger event that IdentityModule listens for
    Event e{};
    e.type = EventType::WHOMAI_REQUEST;
    bus.publish(e);

    // Assert we got exactly one TX
    TEST_ASSERT_EQUAL_MESSAGE(1, txCount, "Identity did not emit JSON_MESSAGE_TX");

    // Basic sanity checks on JSON payload
    TEST_ASSERT_TRUE_MESSAGE(lastTx.find("\"kind\"") != std::string::npos,
                             "Handshake JSON missing 'kind'");
    TEST_ASSERT_TRUE_MESSAGE(lastTx.find("identity") != std::string::npos,
                             "Handshake JSON missing 'identity'");
    TEST_ASSERT_TRUE_MESSAGE(lastTx.find("\"protocol\"") != std::string::npos,
                             "Handshake JSON missing 'protocol'");
    TEST_ASSERT_TRUE_MESSAGE(lastTx.find("\"firmware\"") != std::string::npos,
                             "Handshake JSON missing 'firmware'");
    TEST_ASSERT_TRUE_MESSAGE(lastTx.find("\"board\"") != std::string::npos,
                             "Handshake JSON missing 'board'");
    TEST_ASSERT_TRUE_MESSAGE(lastTx.find("\"name\"") != std::string::npos,
                             "Handshake JSON missing 'name'");

    // OPTIONAL: if you want strict protocol match:
    // TEST_ASSERT_TRUE_MESSAGE(lastTx.find("\"protocol\":1") != std::string::npos,
    //                          "Protocol version mismatch");
}

// Cross-platform test runner
#include "../test_runner.h"

void run_tests() {
    RUN_TEST(test_identity_emits_handshake_on_whoami_request);
}

TEST_RUNNER(run_tests)
