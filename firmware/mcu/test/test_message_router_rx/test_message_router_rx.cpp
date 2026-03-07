#include <unity.h>
#include <vector>
#include <string>
#include <cstring>

#include "core/EventBus.h"
#include "core/Event.h"
#include "command/MessageRouter.h"
#include "core/Protocol.h"
#include "fakes/fakeTransport.h"
#include "support/arduino_stubs.h"




static std::vector<Event> g_events;
static void captureEvent(const Event& evt) { g_events.push_back(evt); }

static std::vector<uint8_t> decode_one_body_or_fail(const std::vector<uint8_t>& tx) {
    std::vector<uint8_t> buf = tx;
    std::vector<uint8_t> body;

    Protocol::extractFrames(buf, [&](const uint8_t* frame, size_t len) {
        body.assign(frame, frame + len);
    });

    TEST_ASSERT_TRUE_MESSAGE(!body.empty(), "No valid Protocol frame decoded from transport.tx");
    return body;
}

static bool find_event(EventType t, Event* out = nullptr) {
    for (auto& e : g_events) {
        if (e.type == t) { if (out) *out = e; return true; }
    }
    return false;
}

void test_router_RX_version_request_sends_version_response(void) {
    EventBus bus;
    FakeTransport transport;
    MessageRouter router(bus, transport);

    g_events.clear();
    bus.subscribe(&captureEvent);

    router.setup();
    test_set_millis(1000);

    uint8_t body[] = { Protocol::MSG_VERSION_REQUEST };
    transport.injectRx(body, sizeof(body));

    TEST_ASSERT_EQUAL_INT(1, transport.sendCount);

    auto outBody = decode_one_body_or_fail(transport.tx);
    TEST_ASSERT_EQUAL_HEX8(Protocol::MSG_VERSION_RESPONSE, outBody[0]);
    TEST_ASSERT_TRUE_MESSAGE(outBody.size() > 1, "Expected VERSION_RESPONSE to include JSON payload");
}

void test_router_RX_whoami_publishes_WHOAMI_REQUEST_event(void) {
    EventBus bus;
    FakeTransport transport;
    MessageRouter router(bus, transport);

    g_events.clear();
    bus.subscribe(&captureEvent);

    router.setup();
    test_set_millis(2000);

    uint8_t body[] = { Protocol::MSG_WHOAMI };
    transport.injectRx(body, sizeof(body));

    TEST_ASSERT_TRUE_MESSAGE(find_event(EventType::WHOMAI_REQUEST), "Did not publish WHOMAI_REQUEST");
}

void test_router_RX_cmd_json_publishes_JSON_MESSAGE_RX_exact_payload(void) {
    EventBus bus;
    FakeTransport transport;
    MessageRouter router(bus, transport);

    g_events.clear();
    bus.subscribe(&captureEvent);

    router.setup();
    test_set_millis(3000);

    const char* json = "{\"cmd\":\"hello\",\"seq\":7}";
    std::vector<uint8_t> body;
    body.push_back(Protocol::MSG_CMD_JSON);
    body.insert(body.end(), (const uint8_t*)json, (const uint8_t*)json + std::strlen(json));

    transport.injectRx(body.data(), body.size());

    Event got{};
    TEST_ASSERT_TRUE_MESSAGE(find_event(EventType::JSON_MESSAGE_RX, &got), "Did not publish JSON_MESSAGE_RX");
    TEST_ASSERT_EQUAL_UINT32(3000, got.timestamp_ms);
    TEST_ASSERT_EQUAL_STRING(json, got.payload.json.c_str());
}

void setUp(void) {}
void tearDown(void) {}

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_router_RX_version_request_sends_version_response);
    RUN_TEST(test_router_RX_whoami_publishes_WHOAMI_REQUEST_event);
    RUN_TEST(test_router_RX_cmd_json_publishes_JSON_MESSAGE_RX_exact_payload);
    return UNITY_END();
}
