// include/core/ServiceContext.h
// Service dependency injection container
//
// =============================================================================
// CROSS-MODULE COUPLING RULES
// =============================================================================
//
// These rules prevent spaghetti dependencies and maintain clear data flow:
//
// 1. HANDLERS → INTENTS (write-only)
//    - Command handlers set intents via IntentBuffer
//    - Handlers do NOT directly control actuators
//    - Handlers do NOT read sensor values
//    Example: MotionHandler calls intents->setVelocityIntent()
//
// 2. CONTROL LOOP → ACTUATORS (consume intents, write signals)
//    - Control loop consumes intents at deterministic rate
//    - Applies control algorithms (PID, state-space)
//    - Writes outputs to SignalBus and actuators
//    - Runs on dedicated FreeRTOS task (Core 1) or cooperative scheduler
//    Example: ControlKernel::step() reads signals, computes control, writes output
//
// 3. TELEMETRY → SIGNALS (read-only snapshots)
//    - Telemetry reads SignalBus snapshots (thread-safe)
//    - Telemetry does NOT compute control logic
//    - Telemetry does NOT modify signals
//    Example: TelemetryModule calls signals.snapshot() for bulk read
//
// 4. SENSORS → SIGNALS (write measurements)
//    - Sensor managers write measurement signals
//    - Use consistent signal naming conventions
//    - Do NOT apply control logic in sensor code
//    Example: EncoderManager writes wheel velocity to SignalBus
//
// 5. SAFETY → MODE (gate all operations)
//    - ModeManager is the single source of truth for robot state
//    - All safety checks go through ModeManager
//    - IntentBuffer cleared on ESTOP/disarm
//    Example: mode.canMove() gates all motion commands
//
// DATA FLOW SUMMARY:
//   Command → Handler → IntentBuffer → ControlLoop → SignalBus → Actuator
//                                                  ↓
//                                            Telemetry (read-only)
//
// =============================================================================

#pragma once

// Forward declarations for HAL
namespace hal {
    class IGpio;
    class IPwm;
    class IServo;
    class II2c;
    class ITimer;
    class IWatchdog;
    class IOta;
    struct HalContext;
}

// Forward declarations for all service types
class EventBus;
class ModeManager;
class GpioManager;
class PwmManager;
class DcMotorManager;
class ServoManager;
class StepperManager;
class MotionController;
class EncoderManager;
class ImuManager;
class LidarManager;
class UltrasonicManager;
class MultiTransport;
class MessageRouter;
class CommandRegistry;
class TelemetryModule;
class ControlModule;
class MCUHost;
class LoopScheduler;
class ObserverManager;

namespace mara {
class IClock;
class IntentBuffer;
}

// Transport types
class UartTransport;
class WifiTransport;
class BleTransport;
namespace mara { class CanTransport; }

// Base class types (using base classes avoids needing inheritance info)
class ICommandHandler;
class IModule;

// Registry singletons (exposed via context for DI access)
class HandlerRegistry;
class ModuleManager;

// Forward declaration in mcu namespace
namespace mara {
    class SensorRegistry;
    class TransportRegistry;
    class ActuatorRegistry;
}
namespace persistence {
    class McuPersistence;
}

namespace mara {

/// ServiceContext provides dependency injection for all services.
/// Instead of using globals, services receive a pointer to this context
/// and access their dependencies through it.
///
/// Services are organized by initialization tier:
/// - Tier 1: No dependencies (core infrastructure)
/// - Tier 2: Motor control (depend on Tier 1)
/// - Tier 3: Sensors
/// - Tier 4: Communication
/// - Tier 5: Orchestration (depend on multiple tiers)
struct ServiceContext {
    // =========================================================================
    // Tier 0: Hardware Abstraction Layer (platform-specific)
    // =========================================================================
    hal::IGpio*     halGpio     = nullptr;   // Platform GPIO abstraction
    hal::IPwm*      halPwm      = nullptr;   // Platform PWM abstraction
    hal::IServo*    halServo    = nullptr;   // Platform servo abstraction
    hal::II2c*      halI2c      = nullptr;   // Platform I2C abstraction (primary bus)
    hal::II2c*      halI2c1     = nullptr;   // Platform I2C abstraction (secondary bus)
    hal::ITimer*    halTimer    = nullptr;   // Platform timer abstraction
    hal::IWatchdog* halWatchdog = nullptr;   // Platform watchdog abstraction
    hal::IOta*      halOta      = nullptr;   // Platform OTA abstraction

    // =========================================================================
    // Tier 1: Core infrastructure (no dependencies)
    // =========================================================================
    IClock*         clock = nullptr;    // Time abstraction (use for all timing)
    IntentBuffer*   intents = nullptr;  // Command intent buffer (for control task)
    EventBus*       bus  = nullptr;
    ModeManager*    mode = nullptr;
    GpioManager*    gpio = nullptr;     // Legacy GPIO manager (uses halGpio internally)
    PwmManager*     pwm  = nullptr;     // Legacy PWM manager (uses halPwm internally)

    // =========================================================================
    // Tier 2: Motor control (depend on GPIO, PWM)
    // =========================================================================
    DcMotorManager*   dcMotor  = nullptr;
    ServoManager*     servo    = nullptr;
    StepperManager*   stepper  = nullptr;
    MotionController* motion   = nullptr;

    // =========================================================================
    // Tier 3: Sensors
    // =========================================================================
    EncoderManager*    encoder    = nullptr;
    ImuManager*        imu        = nullptr;
    LidarManager*      lidar      = nullptr;
    UltrasonicManager* ultrasonic = nullptr;

    // =========================================================================
    // Tier 4: Communication
    // =========================================================================
    MultiTransport*  transport = nullptr;
    MessageRouter*   router    = nullptr;
    CommandRegistry* commands  = nullptr;
    TelemetryModule* telemetry = nullptr;

    // Individual transports (optional, for direct access)
    UartTransport* uart = nullptr;
    WifiTransport* wifi = nullptr;
    BleTransport*  ble  = nullptr;
    CanTransport*  can  = nullptr;

    // =========================================================================
    // Tier 5: Orchestration
    // =========================================================================
    ControlModule* control = nullptr;
    MCUHost*       host    = nullptr;

    // =========================================================================
    // Modules (using IModule* for polymorphic access)
    // =========================================================================
    IModule* heartbeat = nullptr;
    IModule* logger    = nullptr;
    IModule* identity  = nullptr;
    IModule* benchmark = nullptr;  // BenchmarkModule (optional, FEATURE_BENCHMARK)
    ObserverManager* observers = nullptr;

    // =========================================================================
    // Command handlers (using ICommandHandler* for polymorphic access)
    // =========================================================================
    ICommandHandler* safetyHandler    = nullptr;
    ICommandHandler* motionHandler    = nullptr;
    ICommandHandler* gpioHandler      = nullptr;
    ICommandHandler* servoHandler     = nullptr;
    ICommandHandler* stepperHandler   = nullptr;
    ICommandHandler* dcMotorHandler   = nullptr;
    ICommandHandler* sensorHandler    = nullptr;
    ICommandHandler* telemetryHandler = nullptr;
    ICommandHandler* controlHandler   = nullptr;
    ICommandHandler* observerHandler  = nullptr;

    // =========================================================================
    // Loop Schedulers
    // =========================================================================
    LoopScheduler* safetyScheduler   = nullptr;
    LoopScheduler* controlScheduler  = nullptr;
    LoopScheduler* telemetryScheduler = nullptr;

    // =========================================================================
    // Registries (singletons, but exposed for DI access)
    // Note: These are singletons because registration happens in static
    // constructors. Access via context preferred over ::instance().
    // =========================================================================
    HandlerRegistry*   handlerRegistry   = nullptr;
    ModuleManager*     moduleManager     = nullptr;
    SensorRegistry*    sensorRegistry    = nullptr;
    TransportRegistry* transportRegistry = nullptr;
    ActuatorRegistry*  actuatorRegistry  = nullptr;
    persistence::McuPersistence* persistence = nullptr;

    // =========================================================================
    // Convenience methods for null-safety
    // =========================================================================
    bool hasHal() const {
        return halGpio != nullptr && halPwm != nullptr;
    }

    bool hasI2c() const {
        return halI2c != nullptr;
    }

    bool hasMotorControl() const {
        return dcMotor != nullptr && motion != nullptr;
    }

    bool hasSensors() const {
        return encoder != nullptr || imu != nullptr || lidar != nullptr;
    }

    bool hasTransport() const {
        return transport != nullptr && router != nullptr;
    }

    bool isValid() const {
        return bus != nullptr && mode != nullptr;
    }
};

} // namespace mara
