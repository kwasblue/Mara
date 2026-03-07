#pragma once

#include "core/Result.h"

namespace mara {

// Forward declaration
struct ServiceContext;

/// Interface for modular setup components.
/// Each setup module handles a specific initialization domain
/// (WiFi, OTA, Safety, Transport, Motors, Sensors, Telemetry).
class ISetupModule {
public:
    virtual ~ISetupModule() = default;

    /// Returns the name of this setup module for logging.
    virtual const char* name() const = 0;

    /// Returns true if this module is critical for safe operation.
    /// If a critical module fails, the system should halt.
    /// Default: false (non-critical)
    virtual bool isCritical() const { return false; }

    /// Performs setup for this module.
    /// @param ctx The service context with pointers to all services.
    /// @return Result indicating success or specific error.
    virtual Result<void> setup(ServiceContext& ctx) = 0;
};

} // namespace mara
