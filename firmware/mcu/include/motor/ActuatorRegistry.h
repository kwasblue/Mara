// include/motor/ActuatorRegistry.h
// Singleton registry for self-registered actuators
//
// Actuators register via REGISTER_ACTUATOR() macro in static constructors.
// Registry provides unified init, setup, and emergency stop.

#pragma once

#include <cstdint>
#include <cstddef>

namespace mara {

class IActuator;
struct ServiceContext;

/// Singleton registry for all actuators
class ActuatorRegistry {
public:
    static constexpr size_t MAX_ACTUATORS = 8;

    static ActuatorRegistry& instance();

    /// Register an actuator (called by REGISTER_ACTUATOR macro)
    void registerActuator(IActuator* actuator);

    /// Set available capabilities from feature flags
    void setAvailableCaps(uint32_t caps) { availableCaps_ = caps; }
    uint32_t availableCaps() const { return availableCaps_; }

    /// Initialize all registered actuators with ServiceContext
    void initAll(ServiceContext& ctx);

    /// Setup all actuators (configure hardware from Pins::)
    void setupAll();

    /// Emergency stop all actuators
    void stopAll();

    /// Find actuator by name
    IActuator* find(const char* name);
    const IActuator* find(const char* name) const;

    /// Typed actuator lookup
    template<typename T>
    T* get() {
        return static_cast<T*>(find(T::NAME));
    }

    template<typename T>
    const T* get() const {
        return static_cast<const T*>(find(T::NAME));
    }

    /// Number of registered actuators
    size_t count() const { return count_; }

    /// Iteration
    IActuator** begin() { return actuators_; }
    IActuator** end() { return actuators_ + count_; }

private:
    ActuatorRegistry() = default;

    IActuator* actuators_[MAX_ACTUATORS] = {};
    size_t count_ = 0;
    uint32_t availableCaps_ = 0;
    bool initialized_ = false;
};

} // namespace mara

/// Register an actuator class with the global registry
#define REGISTER_ACTUATOR(ClassName) \
    static ClassName __actuator_instance_##ClassName; \
    static struct __actuator_registrar_##ClassName { \
        __actuator_registrar_##ClassName() { \
            mara::ActuatorRegistry::instance().registerActuator(&__actuator_instance_##ClassName); \
        } \
    } __actuator_registrar_obj_##ClassName
