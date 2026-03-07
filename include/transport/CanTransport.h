// include/transport/CanTransport.h
// CAN bus transport with hybrid native/protocol support
//
// Hybrid approach:
//   - CAN-native: Real-time messages (velocity, signals, encoder, IMU)
//     Uses compact 8-byte packed structures for minimal latency
//   - Protocol: JSON commands wrapped in multi-frame transport
//     For configuration, setup, and complex commands
//
// Usage:
//   1. Enable HAS_CAN in platformio.ini
//   2. CanTransport auto-registers via REGISTER_TRANSPORT macro
//   3. Set callbacks for native message handling
//   4. Protocol frames route through standard frame handler

#pragma once

#include "config/FeatureFlags.h"

#if HAS_CAN

#include <vector>
#include <functional>
#include "core/ITransport.h"
#include "TransportRegistry.h"
#include "hal/ICan.h"
#include "config/CanDefs.h"

namespace mara {

// Callback types for native CAN messages
using VelocityCallback = std::function<void(float vx, float omega, uint16_t seq)>;
using SignalCallback = std::function<void(uint16_t id, float value)>;
using HeartbeatCallback = std::function<void(uint8_t nodeId, uint32_t uptime, can::NodeState state)>;
using EncoderCallback = std::function<void(uint8_t nodeId, int32_t counts, int16_t velocity)>;

/**
 * CanTransport - Hybrid CAN transport for real-time and protocol messages
 *
 * Features:
 *   - CAN-native message dispatch for real-time control
 *   - Multi-frame protocol transport for JSON commands
 *   - Automatic frame reassembly for protocol messages
 *   - Node addressing for multi-node networks
 *   - Hardware filtering support
 */
class CanTransport : public IRegisteredTransport {
public:
    CanTransport();
    ~CanTransport() override = default;

    // === ITransport interface ===
    void begin() override;
    void loop() override;
    bool sendBytes(const uint8_t* data, size_t len) override;

    // === IRegisteredTransport interface ===
    const char* name() const override { return "CAN"; }
    uint32_t requiredCaps() const override { return TransportCap::CAN; }
    int priority() const override { return 50; }  // Higher priority for real-time
    void configure() override;

    // === CAN configuration ===

    /// Set HAL CAN interface (must be called before begin)
    void setHal(hal::ICan* can) { can_ = can; }

    /// Set local node ID (0-14, 15 = broadcast)
    void setNodeId(uint8_t id) { nodeId_ = id; }
    uint8_t nodeId() const { return nodeId_; }

    /// Set CAN baud rate (default 500000)
    void setBaudRate(uint32_t baud) { baudRate_ = baud; }

    // === Native message callbacks ===
    void setVelocityCallback(VelocityCallback cb) { onVelocity_ = std::move(cb); }
    void setSignalCallback(SignalCallback cb) { onSignal_ = std::move(cb); }
    void setHeartbeatCallback(HeartbeatCallback cb) { onHeartbeat_ = std::move(cb); }
    void setEncoderCallback(EncoderCallback cb) { onEncoder_ = std::move(cb); }

    // === Native message sending ===

    /// Send velocity command (CAN-native)
    bool sendVelocity(float vx, float omega);

    /// Send signal value (CAN-native)
    bool sendSignal(uint16_t signalId, float value);

    /// Send heartbeat (CAN-native)
    bool sendHeartbeat(uint32_t uptime, can::NodeState state, uint8_t load = 0);

    /// Send encoder feedback (CAN-native)
    bool sendEncoder(int32_t counts, int16_t velocity);

    /// Send E-stop (broadcast, highest priority)
    bool sendEstop();

    /// Send stop command to specific node
    bool sendStop(uint8_t targetNode = can::BROADCAST_ID);

    // === Protocol transport ===

    /// Send protocol frame (JSON command wrapped in multi-frame)
    bool sendProtocol(const uint8_t* data, size_t len, uint8_t targetNode = can::BROADCAST_ID);

    // === Status ===
    bool isConnected() const { return connected_; }
    uint32_t txCount() const { return txCount_; }
    uint32_t rxCount() const { return rxCount_; }
    uint32_t errorCount() const { return errorCount_; }

private:
    // HAL interface
    hal::ICan* can_ = nullptr;

    // Configuration
    uint8_t nodeId_ = 0;
    uint32_t baudRate_ = 500000;
    bool connected_ = false;

    // Statistics
    uint32_t txCount_ = 0;
    uint32_t rxCount_ = 0;
    uint32_t errorCount_ = 0;
    uint16_t txSeq_ = 0;

    // Protocol reassembly
    struct ProtoReassembly {
        uint8_t msgId = 0;
        uint8_t expectedFrames = 0;
        uint8_t receivedMask = 0;
        uint8_t data[can::PROTO_MAX_MSG_SIZE];
        size_t totalLen = 0;
        uint32_t lastFrameTime = 0;

        void reset() {
            msgId = 0;
            expectedFrames = 0;
            receivedMask = 0;
            totalLen = 0;
            lastFrameTime = 0;
        }

        bool isComplete() const {
            if (expectedFrames == 0) return false;
            uint16_t mask = (1 << expectedFrames) - 1;
            return (receivedMask & mask) == mask;
        }
    };
    ProtoReassembly protoRx_[can::MAX_NODE_ID + 1];  // Per-node reassembly
    uint8_t protoTxMsgId_ = 0;

    // Native callbacks
    VelocityCallback onVelocity_;
    SignalCallback onSignal_;
    HeartbeatCallback onHeartbeat_;
    EncoderCallback onEncoder_;

    // Message handling
    void processMessage(const hal::CanMessage& msg);
    void handleNativeMessage(uint16_t id, const uint8_t* data, size_t len);
    void handleProtocolFrame(uint8_t nodeId, const uint8_t* data, size_t len);

    // Protocol transport helpers
    bool sendCanFrame(uint16_t id, const uint8_t* data, size_t len);
};

} // namespace mara

// Auto-register with transport registry
REGISTER_TRANSPORT(mara::CanTransport);

#else // !HAS_CAN

#include "TransportRegistry.h"

namespace mara {

// Stub implementation when CAN is disabled
class CanTransport : public IRegisteredTransport {
public:
    void begin() override {}
    void loop() override {}
    bool sendBytes(const uint8_t*, size_t) override { return false; }
    const char* name() const override { return "CAN"; }
    uint32_t requiredCaps() const override { return 0xFFFFFFFF; }  // Never enabled
};

} // namespace mara

#endif // HAS_CAN
