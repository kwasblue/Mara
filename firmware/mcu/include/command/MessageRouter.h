#pragma once
#include <vector>
#include <Arduino.h>

#include "core/EventBus.h"
#include "core/Event.h"
#include "core/ITransport.h"
#include "core/Protocol.h"
#include "core/Messages.h"

class MessageRouter {
public:
    MessageRouter(EventBus& bus, ITransport& transport);

    void setup();
    void loop();

private:
    EventBus&            bus_;
    ITransport&          transport_;
    std::vector<uint8_t> txBuffer_;

    static MessageRouter* s_instance;
    static void onEventStatic(const Event& evt);

    void onFrame(const uint8_t* frame, size_t len);
    void onEvent(const Event& evt);
    void sendSimple(uint8_t msgType);
    void sendVersionResponse();
};