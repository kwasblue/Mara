#include <unity.h>
#include <string>

#include "core/Messages.h"

void setUp() {}
void tearDown() {}

void test_msgKindFromString() {
    TEST_ASSERT_EQUAL((int)MsgKind::CMD, (int)msgKindFromString("cmd"));
    TEST_ASSERT_EQUAL((int)MsgKind::TELEMETRY, (int)msgKindFromString("telemetry"));
    TEST_ASSERT_EQUAL((int)MsgKind::UNKNOWN, (int)msgKindFromString("nope"));
}

void test_parse_json_cmd_extracts_seq_type_payload() {
    std::string s =
        R"({"kind":"cmd","type":"CMD_SET_VEL","seq":123,"payload":{"vx":1.25,"omega":-0.5}})";

    JsonMessage msg;
    bool ok = parseJsonToMessage(s, msg);
    TEST_ASSERT_TRUE(ok);

    TEST_ASSERT_EQUAL((int)MsgKind::CMD, (int)msg.kind);
    TEST_ASSERT_EQUAL_UINT32(123, msg.seq);
    TEST_ASSERT_EQUAL_STRING("CMD_SET_VEL", msg.typeStr.c_str());

    auto p = msg.payload.as<ArduinoJson::JsonVariantConst>();
    float vx = p["vx"] | 0.0f;
    float omega = p["omega"] | 0.0f;

    TEST_ASSERT_FLOAT_WITHIN(0.0001f, 1.25f, vx);
    TEST_ASSERT_FLOAT_WITHIN(0.0001f, -0.5f, omega);
}

void test_parse_json_invalid_fails() {
    std::string s = R"({"kind":"cmd","type":)";
    JsonMessage msg;
    bool ok = parseJsonToMessage(s, msg);
    TEST_ASSERT_FALSE(ok);
}

#ifdef ARDUINO
#include <Arduino.h>
void setup() {
    UNITY_BEGIN();
    RUN_TEST(test_msgKindFromString);
    RUN_TEST(test_parse_json_cmd_extracts_seq_type_payload);
    RUN_TEST(test_parse_json_invalid_fails);
    UNITY_END();
}
void loop() {}
#else
int main(int, char**) {
    UNITY_BEGIN();
    RUN_TEST(test_msgKindFromString);
    RUN_TEST(test_parse_json_cmd_extracts_seq_type_payload);
    RUN_TEST(test_parse_json_invalid_fails);
    return UNITY_END();
}
#endif
