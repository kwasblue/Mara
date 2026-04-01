#pragma once

#include <Arduino.h>  // For HardwareSerial
#include "core/ITransport.h"

// HAL (Hardware Abstraction Layer)
#include "hal/esp32/Esp32Hal.h"

// Include all necessary headers for service types
#include "core/Clock.h"
#include "core/IntentBuffer.h"
#include "core/EventBus.h"
#include "core/MCUHost.h"
#include "core/LoopScheduler.h"
#include "core/ServiceContext.h"

#include "command/ModeManager.h"
#include "command/MessageRouter.h"
#include "command/CommandRegistry.h"
#include "command/HandlerRegistry.h"
#include "command/handlers/AllHandlers.h"
#include "config/FeatureFlags.h"

#include "hw/GpioManager.h"
#include "hw/PwmManager.h"

#include "motor/DcMotorManager.h"
#include "motor/ServoManager.h"
#include "motor/StepperManager.h"
#include "motor/MotionController.h"

#include "sensor/EncoderManager.h"
#include "sensor/ImuManager.h"
#include "sensor/LidarManager.h"
#include "sensor/UltrasonicManager.h"

#include "transport/MultiTransport.h"
#include "transport/UartTransport.h"
#include "transport/WifiTransport.h"
#include "transport/BleTransport.h"
#include "transport/MqttTransport.h"
#include "transport/CanTransport.h"

#include "module/HeartbeatModule.h"
#include "module/LoggingModule.h"
#include "module/IdentityModule.h"
#include "module/TelemetryModule.h"
#include "module/ControlModule.h"
#include "persistence/McuPersistence.h"

// Optional modules (feature-flagged)
#ifdef FEATURE_BENCHMARK
#include "benchmark/BenchmarkModule.h"
#endif

namespace mara {

// =============================================================================
// SERVICE OWNERSHIP MODEL
// =============================================================================
//
// ServiceStorage is the single owner of all service instances. It manages
// two categories of objects with different ownership semantics:
//
// 1. MEMBER OBJECTS (stack-allocated, automatic lifetime):
//    - clock, intents, bus, mode, gpio, pwm, dcMotor, servo, stepper, motion
//    - encoder, imu, lidar, ultrasonic, transport, telemetry
//    - heartbeat, logger, schedulers
//    These are constructed when ServiceStorage is created and destroyed
//    when ServiceStorage goes out of scope.
//
// 2. HEAP-ALLOCATED OBJECTS (via new, explicit lifetime):
//    - uart, wifi, ble (transports needing runtime config)
//    - router, commands, control, host, identity
//    - All handlers (safetyHandler, motionHandler, etc.)
//    These are created in init*() methods because they need:
//    - Runtime parameters (Serial, port numbers, device name)
//    - Dependencies that must be fully constructed first
//    The destructor deletes all of these.
//
// THREAD SAFETY:
//    - ServiceStorage must be created on a single thread (setup())
//    - ServiceContext pointers can be passed to other threads
//    - Individual services handle their own thread safety
//
// LIFETIME GUARANTEE:
//    - ServiceStorage must outlive all ServiceContext references
//    - In typical embedded use, ServiceStorage is static and lives forever
//
// =============================================================================

/// ServiceStorage owns all service instances.
/// This replaces global variables with a single owning struct.
/// Services are constructed in dependency order.
///
/// Usage:
///   static ServiceStorage storage;
///   storage.initTransports(...);
///   storage.initRouter();
///   storage.initCommands();
///   storage.initControl();
///   storage.initHost(...);
///   ServiceContext ctx = storage.buildContext();
struct ServiceStorage {
    // Non-copyable, non-movable (prevents accidental ownership transfer)
    ServiceStorage() = default;
    ServiceStorage(const ServiceStorage&) = delete;
    ServiceStorage& operator=(const ServiceStorage&) = delete;
    ServiceStorage(ServiceStorage&&) = delete;
    ServiceStorage& operator=(ServiceStorage&&) = delete;

    /// Destructor cleans up all heap-allocated objects.
    /// In typical embedded use (static storage), this is never called.
    /// Included for completeness and testing scenarios.
    ~ServiceStorage();

    // =========================================================================
    // Tier 0: Hardware Abstraction Layer (platform-specific)
    // =========================================================================
    hal::Esp32HalStorage hal;

    // =========================================================================
    // Tier 1: Core infrastructure (no dependencies)
    // =========================================================================
    SystemClock  clock;    // Time abstraction
    IntentBuffer intents;  // Command intent buffer
    EventBus     bus;
    ModeManager  mode;
    GpioManager  gpio;
    PwmManager   pwm;

    // =========================================================================
    // Tier 2: Motor control
    // Constructors take references, so we initialize after gpio/pwm
    // =========================================================================
    DcMotorManager dcMotor{gpio, pwm};
    ServoManager   servo;
    StepperManager stepper{gpio};

    // MotionController needs motors, servo, stepper
    // Default values - can be reconfigured in init()
    MotionController motion{
        dcMotor,
        /*leftMotorId=*/0,
        /*rightMotorId=*/1,
        /*wheelBase=*/0.25f,
        /*maxLinear=*/0.5f,
        /*maxAngular=*/2.0f,
        &servo,
        &stepper
    };

    // =========================================================================
    // Tier 3: Sensors
    // =========================================================================
    EncoderManager    encoder;
    ImuManager        imu;
    LidarManager      lidar;
    UltrasonicManager ultrasonic;

    // =========================================================================
    // Tier 4: Communication
    // =========================================================================
    MultiTransport transport;

    // Note: UartTransport/WifiTransport need HardwareSerial/port at construction
    // These will be initialized separately since they need Arduino runtime
    UartTransport* uart = nullptr;
    WifiTransport* wifi = nullptr;
    BleTransport*  ble  = nullptr;
    MqttTransport* mqtt = nullptr;
    CanTransport*  can  = nullptr;

    // Router depends on bus and transport
    MessageRouter* router = nullptr;

    // Registry depends on bus, mode, motion
    CommandRegistry* commands = nullptr;

    // Telemetry depends on bus
    TelemetryModule telemetry{bus};
    persistence::McuPersistence persistence;

    // =========================================================================
    // Tier 5: Orchestration
    // =========================================================================
    // Control module depends on many services
    ControlModule* control = nullptr;

    // Host depends on bus and router
    MCUHost* host = nullptr;

    // =========================================================================
    // Modules
    // =========================================================================
    HeartbeatModule heartbeat{bus};
    LoggingModule   logger{bus};
    IdentityModule* identity = nullptr;

    // =========================================================================
    // Command Handlers
    // =========================================================================
    SafetyHandler*    safetyHandler    = nullptr;
    MotionHandler*    motionHandler    = nullptr;
    GpioHandler*      gpioHandler      = nullptr;
    ServoHandler*     servoHandler     = nullptr;
    StepperHandler*   stepperHandler   = nullptr;
    DcMotorHandler*   dcMotorHandler   = nullptr;
    SensorHandler*    sensorHandler    = nullptr;
    TelemetryHandler* telemetryHandler = nullptr;
    ControlHandler*   controlHandler   = nullptr;
    ObserverHandler*  observerHandler  = nullptr;
    IdentityHandler*  identityHandler  = nullptr;

#ifdef FEATURE_BENCHMARK
    // =========================================================================
    // Benchmark System (optional, feature-flagged)
    // =========================================================================
    benchmark::BenchmarkModule* benchmarkModule  = nullptr;
    BenchmarkHandler*           benchmarkHandler = nullptr;
#endif

    // =========================================================================
    // Loop Schedulers
    // =========================================================================
    LoopScheduler safetyScheduler{20};    // 20ms = 50Hz
    LoopScheduler controlScheduler{20};   // 20ms = 50Hz
    LoopScheduler telemetryScheduler{1000}; // 1000ms = 1Hz (reduced for WiFi stability)

    // =========================================================================
    // Initialization methods
    // =========================================================================

    /// Initialize HAL and wire it to managers.
    /// Call this first in setup(), before other init methods.
    void initHal() {
        // Wire HAL to managers
        gpio.setHal(&hal.gpio);
        pwm.setHal(&hal.pwm);
        servo.setHal(&hal.servo);
        imu.setHal(&hal.i2c);
        lidar.setHal(&hal.i2c);
        encoder.setHal(&hal.gpio);
        stepper.setHal(&hal.timer);
        mode.setHalGpio(&hal.gpio);
        mode.setHalWatchdog(&hal.watchdog);

        // Wire new HAL components
        persistence.setHal(&hal.persistence, &hal.systemInfo);
    }

    /// Initialize I2C bus via HAL.
    /// Call after initHal() but before sensors need I2C.
    void initI2c(uint8_t sda, uint8_t scl, uint32_t freq = 400000) {
        hal.i2c.begin(sda, scl, freq);
    }

    /// Initialize transports that require runtime parameters.
    /// Call this in setup() after Serial is ready.
    /// mqttBroker can be nullptr to disable MQTT.
    void initTransports(HardwareSerial& serial, uint32_t baud, uint16_t tcpPort,
                        const char* mqttBroker = nullptr, uint16_t mqttPort = 1883,
                        const char* robotId = "node0");

    /// Initialize CAN transport (optional, call after initHal).
    /// @param nodeId Local CAN node ID (0-14)
    /// @param baudRate CAN baud rate (default 500000)
    void initCan(uint8_t nodeId = 0, uint32_t baudRate = 500000);

    /// Initialize router (call after transports are set up).
    void initRouter();

    /// Initialize command registry and handlers.
    void initCommands();

    /// Initialize control module.
    void initControl();

    /// Initialize host and identity module.
    void initHost(const char* deviceName);

    /// Build a ServiceContext from this storage.
    /// Call after all init methods have been called.
    ServiceContext buildContext();
};

} // namespace mara
