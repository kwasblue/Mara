// src/transport/CanTransport.cpp
// CAN bus transport implementation

#include "transport/CanTransport.h"

#if HAS_CAN

#include "utils/Logger.h"
#include <Arduino.h>

static const char* TAG = "CANTransport";

namespace mara {

CanTransport::CanTransport() {
    // Initialize reassembly buffers
    for (auto& rx : protoRx_) {
        rx.reset();
    }
}

void CanTransport::configure() {
    // Configuration is done via setHal(), setNodeId(), etc.
    // Called by TransportRegistry during setup
}

void CanTransport::begin() {
    if (!can_) {
        LOG_ERROR(TAG, "No CAN HAL set");
        return;
    }

    if (!can_->begin(baudRate_)) {
        LOG_ERROR(TAG, "Failed to initialize CAN at %u bps", baudRate_);
        return;
    }

    connected_ = true;
    setEnabled(true);
    LOG_INFO(TAG, "Started (node %u, %u bps)", nodeId_, baudRate_);
}

void CanTransport::loop() {
    if (!can_ || !connected_) return;

    // Check for bus errors
    if (can_->hasError()) {
        hal::CanState state = can_->getState();
        if (state == hal::CanState::BUS_OFF) {
            LOG_WARN(TAG, "Bus off, attempting recovery");
            can_->recover();
        }
    }

    // Process received messages
    hal::CanMessage msg;
    while (can_->available() > 0) {
        if (can_->receive(msg, 0)) {
            rxCount_++;
            processMessage(msg);
        }
    }

    // Timeout stale protocol reassembly (after 500ms)
    uint32_t now = millis();
    for (auto& rx : protoRx_) {
        if (rx.expectedFrames > 0 && (now - rx.lastFrameTime) > 500) {
            LOG_WARN(TAG, "Proto reassembly timeout for msg %u", rx.msgId);
            rx.reset();
        }
    }
}

bool CanTransport::sendBytes(const uint8_t* data, size_t len) {
    // Protocol transport: wrap in multi-frame
    return sendProtocol(data, len, can::BROADCAST_ID);
}

// === Native message sending ===

bool CanTransport::sendVelocity(float vx, float omega) {
    uint8_t data[8];
    can::encodeSetVel(vx, omega, txSeq_++, data);
    return sendCanFrame(can::makeId(can::MsgId::SET_VEL_BASE, nodeId_), data, 8);
}

bool CanTransport::sendSignal(uint16_t signalId, float value) {
    uint8_t data[8];
    can::SetSignalMsg::encode(signalId, value, data);
    return sendCanFrame(can::makeId(can::MsgId::SET_SIGNAL_BASE, nodeId_), data, 8);
}

bool CanTransport::sendHeartbeat(uint32_t uptime, can::NodeState state, uint8_t load) {
    uint8_t data[8];
    can::encodeHeartbeat(uptime, state, load, errorCount_ & 0xFFFF, data);
    return sendCanFrame(can::makeId(can::MsgId::HEARTBEAT_BASE, nodeId_), data, 8);
}

bool CanTransport::sendEncoder(int32_t counts, int16_t velocity) {
    uint8_t data[8];
    can::encodeEncoder(counts, velocity, millis() & 0xFFFF, data);
    return sendCanFrame(can::makeId(can::MsgId::ENCODER_BASE, nodeId_), data, 8);
}

bool CanTransport::sendEstop() {
    // E-stop is broadcast, no payload needed
    return sendCanFrame(can::MsgId::ESTOP, nullptr, 0);
}

bool CanTransport::sendStop(uint8_t targetNode) {
    return sendCanFrame(can::makeId(can::MsgId::STOP_BASE, targetNode), nullptr, 0);
}

// === Protocol transport ===

bool CanTransport::sendProtocol(const uint8_t* data, size_t len, uint8_t targetNode) {
    if (len > can::PROTO_MAX_MSG_SIZE) {
        LOG_WARN(TAG, "Protocol message too large: %u > %u", len, can::PROTO_MAX_MSG_SIZE);
        return false;
    }

    // Calculate number of frames needed
    uint8_t numFrames = (len + can::PROTO_PAYLOAD_SIZE - 1) / can::PROTO_PAYLOAD_SIZE;
    if (numFrames > can::PROTO_MAX_FRAMES) {
        numFrames = can::PROTO_MAX_FRAMES;
    }

    uint8_t msgId = protoTxMsgId_++;
    uint16_t canId = can::makeId(can::MsgId::PROTO_CMD_BASE, targetNode);

    size_t offset = 0;
    for (uint8_t frame = 0; frame < numFrames; frame++) {
        can::ProtoFrame pf;
        pf.header.frame_id = frame;
        pf.header.total_frames = numFrames;
        pf.header.msg_id = msgId;

        size_t chunkLen = len - offset;
        if (chunkLen > can::PROTO_PAYLOAD_SIZE) {
            chunkLen = can::PROTO_PAYLOAD_SIZE;
        }

        memcpy(pf.payload, data + offset, chunkLen);
        // Zero-pad remaining bytes
        if (chunkLen < can::PROTO_PAYLOAD_SIZE) {
            memset(pf.payload + chunkLen, 0, can::PROTO_PAYLOAD_SIZE - chunkLen);
        }

        if (!sendCanFrame(canId, reinterpret_cast<uint8_t*>(&pf), 8)) {
            LOG_WARN(TAG, "Failed to send proto frame %u/%u", frame + 1, numFrames);
            return false;
        }

        offset += chunkLen;
    }

    return true;
}

// === Private helpers ===

bool CanTransport::sendCanFrame(uint16_t id, const uint8_t* data, size_t len) {
    if (!can_ || !connected_) return false;

    hal::CanMessage msg;
    msg.id = id;
    msg.len = (len > 8) ? 8 : len;
    msg.extended = false;
    msg.rtr = false;

    if (data && len > 0) {
        memcpy(msg.data, data, msg.len);
    }

    if (can_->send(msg, 10)) {
        txCount_++;
        return true;
    }

    errorCount_++;
    return false;
}

void CanTransport::processMessage(const hal::CanMessage& msg) {
    uint16_t id = msg.id;

    // Check if this is a protocol frame
    if ((id & 0xFF0) == can::MsgId::PROTO_CMD_BASE ||
        (id & 0xFF0) == can::MsgId::PROTO_RSP_BASE) {
        uint8_t srcNode = can::extractNodeId(id);
        handleProtocolFrame(srcNode, msg.data, msg.len);
        return;
    }

    // Handle native messages
    handleNativeMessage(id, msg.data, msg.len);
}

void CanTransport::handleNativeMessage(uint16_t id, const uint8_t* data, size_t len) {
    uint8_t nodeId = can::extractNodeId(id);
    uint16_t baseId = id & 0xFF0;

    switch (baseId) {
        case can::MsgId::ESTOP:
            LOG_WARN(TAG, "E-STOP received!");
            if (onEstop_) {
                onEstop_();
            }
            break;

        case can::MsgId::SET_VEL_BASE:
            if (len >= sizeof(can::SetVelMsg) && onVelocity_) {
                can::SetVelMsg msg;
                memcpy(&msg, data, sizeof(msg));
                float vx, omega;
                msg.toFloats(vx, omega);
                onVelocity_(vx, omega, msg.seq);
            }
            break;

        case can::MsgId::SET_SIGNAL_BASE:
            if (len >= sizeof(can::SetSignalMsg) && onSignal_) {
                can::SetSignalMsg msg;
                memcpy(&msg, data, sizeof(msg));
                onSignal_(msg.signal_id, msg.value);
            }
            break;

        case can::MsgId::HEARTBEAT_BASE:
            if (len >= sizeof(can::HeartbeatMsg) && onHeartbeat_) {
                can::HeartbeatMsg msg;
                memcpy(&msg, data, sizeof(msg));
                onHeartbeat_(nodeId, msg.uptime_ms, static_cast<can::NodeState>(msg.state));
            }
            break;

        case can::MsgId::ENCODER_BASE:
            if (len >= sizeof(can::EncoderMsg) && onEncoder_) {
                can::EncoderMsg msg;
                memcpy(&msg, data, sizeof(msg));
                onEncoder_(nodeId, msg.counts, msg.velocity);
            }
            break;

        case can::MsgId::STOP_BASE:
            LOG_DEBUG(TAG, "Stop command from node %u", nodeId);
            if (onStop_) {
                onStop_(nodeId);
            }
            break;

        default:
            LOG_DEBUG(TAG, "Unknown CAN ID 0x%03X", id);
            break;
    }
}

void CanTransport::handleProtocolFrame(uint8_t srcNode, const uint8_t* data, size_t len) {
    if (len < sizeof(can::ProtoFrame)) {
        LOG_WARN(TAG, "Proto frame too short: %u", len);
        return;
    }

    can::ProtoFrame pf;
    memcpy(&pf, data, sizeof(pf));

    uint8_t frameId = pf.header.frame_id;
    uint8_t totalFrames = pf.header.total_frames;
    uint8_t msgId = pf.header.msg_id;

    if (frameId >= can::PROTO_MAX_FRAMES || totalFrames > can::PROTO_MAX_FRAMES) {
        LOG_WARN(TAG, "Invalid proto frame: %u/%u", frameId, totalFrames);
        return;
    }

    // Get reassembly buffer for this source node
    ProtoReassembly& rx = protoRx_[srcNode & can::MAX_NODE_ID];

    // Check if this is a new message or continuation
    if (rx.msgId != msgId || rx.expectedFrames != totalFrames) {
        // New message, reset buffer
        rx.reset();
        rx.msgId = msgId;
        rx.expectedFrames = totalFrames;
    }

    // Store frame data
    size_t offset = frameId * can::PROTO_PAYLOAD_SIZE;
    memcpy(rx.data + offset, pf.payload, can::PROTO_PAYLOAD_SIZE);
    rx.receivedMask |= (1 << frameId);
    rx.lastFrameTime = millis();

    // Update total length (last frame determines actual length)
    if (frameId == totalFrames - 1) {
        rx.totalLen = offset + can::PROTO_PAYLOAD_SIZE;
        // Trim trailing zeros to find actual length
        while (rx.totalLen > 0 && rx.data[rx.totalLen - 1] == 0) {
            rx.totalLen--;
        }
    }

    // Check if message is complete
    if (rx.isComplete()) {
        LOG_DEBUG(TAG, "Proto message complete: %u bytes from node %u", rx.totalLen, srcNode);

        // Dispatch to frame handler
        if (handler_ && rx.totalLen > 0) {
            handler_(rx.data, rx.totalLen);
        }

        rx.reset();
    }
}

} // namespace mara

#endif // HAS_CAN
