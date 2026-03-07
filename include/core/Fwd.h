// include/core/Fwd.h
// Forward declarations for core types
//
// Include this header when you only need type names for pointers/references,
// not the full definition. This reduces compile times and circular dependencies.

#pragma once

// Core infrastructure
namespace mara {
    class IClock;
    class SystemClock;
    class IntentBuffer;
    class IModule;
    class ITransport;
    class LoopScheduler;
    class ModuleManager;
    struct ServiceContext;

    // Real-time stats
    struct RtTimingStats;
}

// Event system
class EventBus;
struct Event;

// Command system
class ModeManager;
class MessageRouter;
class CommandRegistry;
class HandlerRegistry;
class ICommandHandler;
class IStringHandler;
struct CommandContext;

// Motor control
class DcMotorManager;
class ServoManager;
class StepperManager;
class MotionController;

// Sensors
class EncoderManager;
class ImuManager;
class LidarManager;
class UltrasonicManager;

// Transport
class MultiTransport;
class UartTransport;
class WifiTransport;
class BleTransport;

// Modules
class MCUHost;
class TelemetryModule;
class ControlModule;
class HeartbeatModule;
class LoggingModule;
class IdentityModule;

// Control system
class SignalBus;
class ControlKernel;
class ObserverManager;

// Hardware
class GpioManager;
class PwmManager;
