// src/transport/TransportRegistry.cpp
// TransportRegistry implementation

#include "transport/TransportRegistry.h"
#include "transport/MultiTransport.h"
#include <cstring>
#include <algorithm>

namespace mara {

TransportRegistry& TransportRegistry::instance() {
    static TransportRegistry s_instance;
    return s_instance;
}

void TransportRegistry::registerTransport(IRegisteredTransport* transport) {
    if (!transport || count_ >= MAX_TRANSPORTS) {
        return;
    }

    // Check for duplicate
    for (size_t i = 0; i < count_; ++i) {
        if (transports_[i] == transport) {
            return;
        }
    }

    transports_[count_++] = transport;
}

void TransportRegistry::beginAll() {
    if (initialized_) {
        return;
    }

    // Sort by priority (lower = earlier)
    std::sort(transports_, transports_ + count_,
        [](IRegisteredTransport* a, IRegisteredTransport* b) {
            return a->priority() < b->priority();
        });

    // Configure and begin each transport that has required capabilities
    for (size_t i = 0; i < count_; ++i) {
        IRegisteredTransport* t = transports_[i];
        uint32_t required = t->requiredCaps();

        // Skip if required capabilities not available
        if ((required & availableCaps_) != required) {
            t->setEnabled(false);
            continue;
        }

        t->setEnabled(true);
        t->configure();
        t->begin();
    }

    initialized_ = true;
}

void TransportRegistry::loopAll() {
    for (size_t i = 0; i < count_; ++i) {
        IRegisteredTransport* t = transports_[i];
        if (t->isEnabled()) {
            t->loop();
        }
    }
}

void TransportRegistry::wireToMultiTransport(MultiTransport* multi) {
    if (!multi) return;

    for (size_t i = 0; i < count_; ++i) {
        IRegisteredTransport* t = transports_[i];
        uint32_t required = t->requiredCaps();

        // Only add if capabilities available
        if ((required & availableCaps_) == required) {
            multi->addTransport(t);
            t->setEnabled(true);
        }
    }
}

IRegisteredTransport* TransportRegistry::find(const char* name) {
    if (!name) return nullptr;

    for (size_t i = 0; i < count_; ++i) {
        if (strcmp(transports_[i]->name(), name) == 0) {
            return transports_[i];
        }
    }
    return nullptr;
}

} // namespace mara
