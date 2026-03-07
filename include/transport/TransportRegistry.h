// include/transport/TransportRegistry.h
// Self-registration registry for transports
//
// Transports register via REGISTER_TRANSPORT() macro.
// Registry integrates with MultiTransport for unified routing.

#pragma once

#include <cstdint>
#include <cstddef>
#include "core/ITransport.h"

// Forward declaration
class MultiTransport;

namespace mara {

/// Capability flags for transports
namespace TransportCap {
    constexpr uint32_t NONE = 0;
    constexpr uint32_t UART = (1 << 0);
    constexpr uint32_t WIFI = (1 << 1);
    constexpr uint32_t BLE  = (1 << 2);
    constexpr uint32_t MQTT = (1 << 3);
    constexpr uint32_t CAN  = (1 << 4);
}

/// Extended transport interface for self-registration
class IRegisteredTransport : public ITransport {
public:
    virtual const char* name() const = 0;
    virtual uint32_t requiredCaps() const { return 0; }
    virtual int priority() const { return 100; }

    /// Called after registration to configure from MaraConfig
    virtual void configure() {}

    bool isEnabled() const { return enabled_; }
    void setEnabled(bool e) { enabled_ = e; }

protected:
    bool enabled_ = false;
};

/// Singleton registry for self-registered transports
class TransportRegistry {
public:
    static constexpr size_t MAX_TRANSPORTS = 8;

    static TransportRegistry& instance();

    /// Register a transport (called by REGISTER_TRANSPORT macro)
    void registerTransport(IRegisteredTransport* transport);

    /// Set available capabilities from feature flags
    void setAvailableCaps(uint32_t caps) { availableCaps_ = caps; }
    uint32_t availableCaps() const { return availableCaps_; }

    /// Configure and begin all enabled transports
    void beginAll();

    /// Poll all enabled transports
    void loopAll();

    /// Wire all enabled transports to a MultiTransport
    void wireToMultiTransport(MultiTransport* multi);

    /// Find transport by name
    IRegisteredTransport* find(const char* name);

    /// Number of registered transports
    size_t count() const { return count_; }

    /// Iteration
    IRegisteredTransport** begin() { return transports_; }
    IRegisteredTransport** end() { return transports_ + count_; }

private:
    TransportRegistry() = default;

    IRegisteredTransport* transports_[MAX_TRANSPORTS] = {};
    size_t count_ = 0;
    uint32_t availableCaps_ = 0;
    bool initialized_ = false;
};

} // namespace mara

/// Register a transport class with the global registry
#define REGISTER_TRANSPORT(ClassName) \
    static ClassName __transport_instance_##ClassName; \
    static struct __transport_registrar_##ClassName { \
        __transport_registrar_##ClassName() { \
            mara::TransportRegistry::instance().registerTransport(&__transport_instance_##ClassName); \
        } \
    } __transport_registrar_obj_##ClassName
