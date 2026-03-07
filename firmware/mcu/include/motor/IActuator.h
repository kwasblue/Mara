// include/motor/IActuator.h
// Base interface for self-registering actuators
//
// Actuators implement this interface and use REGISTER_ACTUATOR() to auto-register.
// Dependencies (GpioManager, PwmManager) come from ServiceContext in init().

#pragma once

#include <cstdint>

namespace mara {

struct ServiceContext;

/// Capability flags for actuators
namespace ActuatorCap {
    constexpr uint32_t NONE     = 0;
    constexpr uint32_t DC_MOTOR = (1 << 0);
    constexpr uint32_t SERVO    = (1 << 1);
    constexpr uint32_t STEPPER  = (1 << 2);
    constexpr uint32_t ENCODER  = (1 << 3);
}

/// Base interface for all actuators
class IActuator {
public:
    virtual ~IActuator() = default;

    /// Unique actuator name (e.g., "dc_motor", "servo", "stepper")
    virtual const char* name() const = 0;

    /// Initialize with dependencies from ServiceContext
    /// Called once during ActuatorRegistry::initAll()
    virtual void init(ServiceContext& ctx) = 0;

    /// Configure hardware (attach pins, set up PWM channels)
    /// Called after init(), uses Pins:: constants
    virtual void setup() = 0;

    /// Stop all outputs (called on ESTOP)
    virtual void stopAll() = 0;

    /// Required capability flags (for feature gating)
    virtual uint32_t requiredCaps() const { return 0; }

    /// Priority for init ordering (lower = earlier). Default 100.
    virtual int priority() const { return 100; }

    /// Whether actuator initialized successfully
    virtual bool isOnline() const { return online_; }

protected:
    bool online_ = false;
};

} // namespace mara
