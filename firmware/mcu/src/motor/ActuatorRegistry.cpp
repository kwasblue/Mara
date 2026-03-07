// src/motor/ActuatorRegistry.cpp
// ActuatorRegistry implementation

#include "motor/ActuatorRegistry.h"
#include "motor/IActuator.h"
#include "core/ServiceContext.h"
#include <cstring>
#include <algorithm>

namespace mara {

ActuatorRegistry& ActuatorRegistry::instance() {
    static ActuatorRegistry s_instance;
    return s_instance;
}

void ActuatorRegistry::registerActuator(IActuator* actuator) {
    if (!actuator || count_ >= MAX_ACTUATORS) {
        return;
    }

    // Check for duplicate
    for (size_t i = 0; i < count_; ++i) {
        if (actuators_[i] == actuator) {
            return;
        }
    }

    actuators_[count_++] = actuator;
}

void ActuatorRegistry::initAll(ServiceContext& ctx) {
    if (initialized_) {
        return;
    }

    // Sort by priority (lower = earlier)
    std::sort(actuators_, actuators_ + count_,
        [](IActuator* a, IActuator* b) {
            return a->priority() < b->priority();
        });

    // Initialize each actuator that has required capabilities
    for (size_t i = 0; i < count_; ++i) {
        IActuator* actuator = actuators_[i];
        uint32_t required = actuator->requiredCaps();

        // Skip if required capabilities not available
        if ((required & availableCaps_) != required) {
            continue;
        }

        actuator->init(ctx);
    }

    initialized_ = true;
}

void ActuatorRegistry::setupAll() {
    for (size_t i = 0; i < count_; ++i) {
        IActuator* actuator = actuators_[i];
        uint32_t required = actuator->requiredCaps();

        // Skip disabled actuators
        if ((required & availableCaps_) != required) {
            continue;
        }

        if (actuator->isOnline()) {
            actuator->setup();
        }
    }
}

void ActuatorRegistry::stopAll() {
    for (size_t i = 0; i < count_; ++i) {
        IActuator* actuator = actuators_[i];
        if (actuator->isOnline()) {
            actuator->stopAll();
        }
    }
}

IActuator* ActuatorRegistry::find(const char* name) {
    if (!name) return nullptr;

    for (size_t i = 0; i < count_; ++i) {
        if (strcmp(actuators_[i]->name(), name) == 0) {
            return actuators_[i];
        }
    }
    return nullptr;
}

const IActuator* ActuatorRegistry::find(const char* name) const {
    if (!name) return nullptr;

    for (size_t i = 0; i < count_; ++i) {
        if (strcmp(actuators_[i]->name(), name) == 0) {
            return actuators_[i];
        }
    }
    return nullptr;
}

} // namespace mara
