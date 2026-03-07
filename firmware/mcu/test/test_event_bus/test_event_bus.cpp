#include <unity.h>
#include <vector>
#include <string>

#include "core/EventBus.h"
#include "core/Event.h"

static std::vector<std::string> calls;
static std::vector<EventType> receivedTypes;

static void handlerA(const Event&) { calls.push_back("A"); }
static void handlerB(const Event&) { calls.push_back("B"); }
static void handlerCapture(const Event& evt) {
    calls.push_back("C");
    receivedTypes.push_back(evt.type);
}

void setUp() {
    calls.clear();
    receivedTypes.clear();
}
void tearDown() {}

// -----------------------------------------------------------------------------
// Basic functionality tests
// -----------------------------------------------------------------------------

void test_eventbus_calls_handlers_in_order() {
    EventBus bus;
    bus.subscribe(handlerA);
    bus.subscribe(handlerB);

    Event evt{};
    evt.type = EventType::PING;
    evt.timestamp_ms = 123;

    bus.publish(evt);

    TEST_ASSERT_EQUAL_INT(2, (int)calls.size());
    TEST_ASSERT_EQUAL_STRING("A", calls[0].c_str());
    TEST_ASSERT_EQUAL_STRING("B", calls[1].c_str());
}

void test_eventbus_ignores_null_handler() {
    EventBus bus;
    bus.subscribe(nullptr);
    bus.subscribe(handlerA);

    Event evt{};
    evt.type = EventType::PING;

    bus.publish(evt);

    TEST_ASSERT_EQUAL_INT(1, (int)calls.size());
    TEST_ASSERT_EQUAL_STRING("A", calls[0].c_str());
}

// -----------------------------------------------------------------------------
// Event type filtering tests
// -----------------------------------------------------------------------------

void test_eventbus_type_filter_receives_matching_events() {
    EventBus bus;
    bus.subscribe(handlerCapture, EventType::PING);

    Event ping{};
    ping.type = EventType::PING;
    bus.publish(ping);

    TEST_ASSERT_EQUAL_INT(1, (int)calls.size());
    TEST_ASSERT_EQUAL_STRING("C", calls[0].c_str());
}

void test_eventbus_type_filter_ignores_non_matching_events() {
    EventBus bus;
    bus.subscribe(handlerCapture, EventType::PING);

    Event pong{};
    pong.type = EventType::PONG;
    bus.publish(pong);

    TEST_ASSERT_EQUAL_INT(0, (int)calls.size());
}

void test_eventbus_all_events_receives_everything() {
    EventBus bus;
    bus.subscribe(handlerCapture);  // Default: ALL_EVENTS

    Event ping{};
    ping.type = EventType::PING;
    bus.publish(ping);

    Event pong{};
    pong.type = EventType::PONG;
    bus.publish(pong);

    TEST_ASSERT_EQUAL_INT(2, (int)calls.size());
    TEST_ASSERT_EQUAL_UINT8(static_cast<uint8_t>(EventType::PING),
                            static_cast<uint8_t>(receivedTypes[0]));
    TEST_ASSERT_EQUAL_UINT8(static_cast<uint8_t>(EventType::PONG),
                            static_cast<uint8_t>(receivedTypes[1]));
}

// -----------------------------------------------------------------------------
// Queue functionality tests
// -----------------------------------------------------------------------------

void test_eventbus_queued_events_not_delivered_until_drain() {
    EventBus bus;
    bus.subscribe(handlerA);

    Event evt{};
    evt.type = EventType::PING;

    bool queued = bus.publishQueued(evt);
    TEST_ASSERT_TRUE(queued);
    TEST_ASSERT_EQUAL_INT(0, (int)calls.size());  // Not delivered yet

    bus.drain();
    TEST_ASSERT_EQUAL_INT(1, (int)calls.size());  // Now delivered
}

void test_eventbus_drain_processes_multiple_events() {
    EventBus bus;
    bus.subscribe(handlerCapture);

    Event ping{};
    ping.type = EventType::PING;
    Event pong{};
    pong.type = EventType::PONG;

    bus.publishQueued(ping);
    bus.publishQueued(pong);
    TEST_ASSERT_EQUAL_INT(0, (int)calls.size());

    bus.drain();
    TEST_ASSERT_EQUAL_INT(2, (int)calls.size());
    TEST_ASSERT_EQUAL_UINT8(static_cast<uint8_t>(EventType::PING),
                            static_cast<uint8_t>(receivedTypes[0]));
    TEST_ASSERT_EQUAL_UINT8(static_cast<uint8_t>(EventType::PONG),
                            static_cast<uint8_t>(receivedTypes[1]));
}

void test_eventbus_queue_full_returns_false() {
    EventBus bus;
    bus.subscribe(handlerA);

    Event evt{};
    evt.type = EventType::PING;

    // Fill the queue (QUEUE_SIZE - 1 because ring buffer needs 1 slot)
    for (int i = 0; i < EventBus::QUEUE_SIZE - 1; ++i) {
        bool ok = bus.publishQueued(evt);
        TEST_ASSERT_TRUE_MESSAGE(ok, "Queue should accept event");
    }

    // Next one should fail
    bool overflow = bus.publishQueued(evt);
    TEST_ASSERT_FALSE_MESSAGE(overflow, "Queue should be full");
}

void test_eventbus_queue_depth_tracking() {
    EventBus bus;

    TEST_ASSERT_EQUAL_UINT8(0, bus.queueDepth());
    TEST_ASSERT_TRUE(bus.queueEmpty());

    Event evt{};
    evt.type = EventType::PING;

    bus.publishQueued(evt);
    TEST_ASSERT_EQUAL_UINT8(1, bus.queueDepth());
    TEST_ASSERT_FALSE(bus.queueEmpty());

    bus.publishQueued(evt);
    TEST_ASSERT_EQUAL_UINT8(2, bus.queueDepth());

    bus.drain();
    TEST_ASSERT_EQUAL_UINT8(0, bus.queueDepth());
    TEST_ASSERT_TRUE(bus.queueEmpty());
}

// -----------------------------------------------------------------------------
// Statistics tests
// -----------------------------------------------------------------------------

void test_eventbus_stats_published_count() {
    EventBus bus;
    bus.subscribe(handlerA);

    Event evt{};
    evt.type = EventType::PING;

    bus.publish(evt);
    bus.publishQueued(evt);
    bus.drain();

    const auto& stats = bus.stats();
    TEST_ASSERT_EQUAL_UINT32(2, stats.published);
}

void test_eventbus_stats_delivered_count() {
    EventBus bus;
    bus.subscribe(handlerA);
    bus.subscribe(handlerB);

    Event evt{};
    evt.type = EventType::PING;

    bus.publish(evt);  // Delivered to 2 handlers

    const auto& stats = bus.stats();
    TEST_ASSERT_EQUAL_UINT32(2, stats.delivered);
}

void test_eventbus_stats_dropped_count() {
    EventBus bus;

    Event evt{};
    evt.type = EventType::PING;

    // Fill queue
    for (int i = 0; i < EventBus::QUEUE_SIZE - 1; ++i) {
        bus.publishQueued(evt);
    }

    // Overflow
    bus.publishQueued(evt);
    bus.publishQueued(evt);

    const auto& stats = bus.stats();
    TEST_ASSERT_EQUAL_UINT32(2, stats.dropped);
}

void test_eventbus_stats_queue_peak() {
    EventBus bus;

    Event evt{};
    evt.type = EventType::PING;

    bus.publishQueued(evt);
    bus.publishQueued(evt);
    bus.publishQueued(evt);

    const auto& stats = bus.stats();
    TEST_ASSERT_EQUAL_UINT32(3, stats.queuePeak);

    // Drain and add more - peak should stay at previous high
    bus.drain();
    bus.publishQueued(evt);

    TEST_ASSERT_EQUAL_UINT32(3, bus.stats().queuePeak);
}

void test_eventbus_stats_reset() {
    EventBus bus;
    bus.subscribe(handlerA);

    Event evt{};
    evt.type = EventType::PING;
    bus.publish(evt);

    TEST_ASSERT_EQUAL_UINT32(1, bus.stats().published);

    bus.resetStats();

    TEST_ASSERT_EQUAL_UINT32(0, bus.stats().published);
    TEST_ASSERT_EQUAL_UINT32(0, bus.stats().delivered);
    TEST_ASSERT_EQUAL_UINT32(0, bus.stats().dropped);
    TEST_ASSERT_EQUAL_UINT32(0, bus.stats().queuePeak);
}

// -----------------------------------------------------------------------------
// Test runner
// -----------------------------------------------------------------------------

#include "../test_runner.h"

void run_tests() {
    // Basic
    RUN_TEST(test_eventbus_calls_handlers_in_order);
    RUN_TEST(test_eventbus_ignores_null_handler);

    // Filtering
    RUN_TEST(test_eventbus_type_filter_receives_matching_events);
    RUN_TEST(test_eventbus_type_filter_ignores_non_matching_events);
    RUN_TEST(test_eventbus_all_events_receives_everything);

    // Queue
    RUN_TEST(test_eventbus_queued_events_not_delivered_until_drain);
    RUN_TEST(test_eventbus_drain_processes_multiple_events);
    RUN_TEST(test_eventbus_queue_full_returns_false);
    RUN_TEST(test_eventbus_queue_depth_tracking);

    // Stats
    RUN_TEST(test_eventbus_stats_published_count);
    RUN_TEST(test_eventbus_stats_delivered_count);
    RUN_TEST(test_eventbus_stats_dropped_count);
    RUN_TEST(test_eventbus_stats_queue_peak);
    RUN_TEST(test_eventbus_stats_reset);
}

TEST_RUNNER(run_tests)
