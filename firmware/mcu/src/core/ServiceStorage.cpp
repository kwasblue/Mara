// src/core/ServiceStorage.cpp
// ServiceStorage implementation - service ownership and initialization

#include "core/ServiceStorage.h"
#include "command/HandlerRegistry.h"
#include "core/ModuleManager.h"
#include "sensor/SensorRegistry.h"
#include "transport/TransportRegistry.h"
#include "motor/ActuatorRegistry.h"
#include "config/FeatureFlags.h"
#include "transport/MqttTransport.h"
#include "transport/CanTransport.h"

// Handler includes (for instantiation)
#include "command/handlers/SafetyHandler.h"
#include "command/handlers/MotionHandler.h"
#include "command/handlers/GpioHandler.h"
#include "command/handlers/ServoHandler.h"
#include "command/handlers/StepperHandler.h"
#include "command/handlers/DcMotorHandler.h"
#include "command/handlers/SensorHandler.h"
#include "command/handlers/TelemetryHandler.h"
#include "command/handlers/ControlHandler.h"
#include "command/handlers/ObserverHandler.h"
#include "command/handlers/IdentityHandler.h"
#ifdef FEATURE_BENCHMARK
#include "command/handlers/BenchmarkHandler.h"
#endif

namespace mara {

ServiceStorage::~ServiceStorage() {
    // Delete in reverse dependency order (Tier 5 → Tier 1)

    // Handlers
    delete identityHandler;
    delete observerHandler;
    delete controlHandler;
    delete telemetryHandler;
    delete sensorHandler;
    delete dcMotorHandler;
    delete stepperHandler;
    delete servoHandler;
    delete gpioHandler;
    delete motionHandler;
    delete safetyHandler;
#ifdef FEATURE_BENCHMARK
    delete benchmarkHandler;
    delete benchmarkModule;
#endif

    // Modules
    delete identity;

    // Tier 5
    delete host;
    delete control;

    // Tier 4
    delete commands;
    delete router;
    delete can;
    delete mqtt;
    delete ble;
    delete wifi;
    delete uart;
}

void ServiceStorage::initTransports(const hal::UartTransportConfig& uartConfig,
                                    const hal::WifiTransportConfig& wifiConfig,
                                    const hal::BleTransportConfig& bleConfig,
                                    const hal::MqttTransportConfig& mqttConfig) {
    // Use HAL transport factory to create transports
    hal::ITransportFactory* factory = &hal.transportFactory;

    uart = static_cast<UartTransport*>(factory->createUart(uartConfig));
    wifi = static_cast<WifiTransport*>(factory->createWifi(wifiConfig));

#if HAS_BLE
    ble = static_cast<BleTransport*>(factory->createBle(bleConfig));
#else
    (void)bleConfig;
#endif

#if HAS_MQTT_TRANSPORT && HAS_WIFI
    if (mqttConfig.broker != nullptr) {
        mqtt = static_cast<MqttTransport*>(factory->createMqtt(mqttConfig));
    }
#else
    (void)mqttConfig;
#endif

    if (uart) transport.addTransport(uart);
    if (wifi) transport.addTransport(wifi);
#if HAS_BLE
    if (ble) transport.addTransport(ble);
#endif
#if HAS_MQTT_TRANSPORT && HAS_WIFI
    if (mqtt) transport.addTransport(mqtt);
#endif
}

void ServiceStorage::initCan(uint8_t nodeId, uint32_t baudRate) {
#if HAS_CAN
    can = new CanTransport();
    can->setHal(&hal.can);
    can->setNodeId(nodeId);
    can->setBaudRate(baudRate);

    // Wire CAN safety callbacks to ModeManager
    can->setEstopCallback([this]() {
        mode.estop();
    });
    can->setStopCallback([this](uint8_t /* nodeId */) {
        mode.deactivate(clock.millis());
    });

    transport.addTransport(can);
#else
    (void)nodeId;
    (void)baudRate;
#endif
}

void ServiceStorage::initRouter() {
    router = new MessageRouter(bus, transport);
}

void ServiceStorage::initCommands() {
    commands = new CommandRegistry(bus, mode, motion);
    commands->setIntentBuffer(&intents);
    commands->setPersistence(&persistence);
    commands->setHandlerRegistry(&HandlerRegistry::instance());  // Explicit wiring

    // Create handlers with default constructors (dependencies injected via init())
    safetyHandler    = new SafetyHandler();
    motionHandler    = new MotionHandler();
    gpioHandler      = new GpioHandler();
    servoHandler     = new ServoHandler();
    stepperHandler   = new StepperHandler();
    dcMotorHandler   = new DcMotorHandler();
    sensorHandler    = new SensorHandler();
    telemetryHandler = new TelemetryHandler();
    controlHandler   = new ControlHandler();
    observerHandler  = new ObserverHandler();
    identityHandler  = new IdentityHandler();

    // Register handlers with CommandRegistry
    commands->registerHandler(safetyHandler);
    commands->registerHandler(motionHandler);
    commands->registerHandler(gpioHandler);
    commands->registerHandler(servoHandler);
    commands->registerHandler(stepperHandler);
    commands->registerHandler(dcMotorHandler);
    commands->registerHandler(sensorHandler);
    commands->registerHandler(telemetryHandler);
    commands->registerHandler(controlHandler);
    commands->registerHandler(observerHandler);
    commands->registerHandler(identityHandler);

#ifdef FEATURE_BENCHMARK
    // Create benchmark module and handler
    benchmarkModule  = new benchmark::BenchmarkModule(bus);
    benchmarkHandler = new BenchmarkHandler();
    commands->registerHandler(benchmarkHandler);

    // Register telemetry provider
    benchmarkModule->registerTelemetry(&telemetry);
#endif

    // Set available capabilities from feature flags
    HandlerRegistry::instance().setAvailableCaps(buildCapabilityMask());

    // Finalize self-registered string handlers
    HandlerRegistry::instance().finalize();
}

void ServiceStorage::initHandlers(ServiceContext& ctx) {
    // Initialize all command handlers with dependencies
    if (commands) {
        commands->initAll(ctx);
    }
}

void ServiceStorage::initControl() {
    control = new ControlModule(
        &bus,
        &mode,
        &motion,
        &encoder,
        &imu,
        &telemetry
    );

    // Wire control module to handlers
    if (controlHandler) {
        controlHandler->setControlModule(control);
    }
    if (observerHandler) {
        observerHandler->setControlModule(control);
    }
    if (commands) {
        commands->setControlModule(control);
    }
}

void ServiceStorage::initHost(const char* deviceName) {
    host = new MCUHost(bus, router);
    identity = new IdentityModule(bus, transport, deviceName);
}

ServiceContext ServiceStorage::buildContext() {
    ServiceContext ctx;

    // Tier 0: HAL
    ctx.halGpio     = &hal.gpio;
    ctx.halPwm      = &hal.pwm;
    ctx.halServo    = &hal.servo;
    ctx.halI2c      = &hal.i2c;
    ctx.halI2c1     = &hal.i2c1;
    ctx.halTimer    = &hal.timer;
    ctx.halWatchdog = &hal.watchdog;
    ctx.halLogger   = &hal.logger;
    ctx.halClock    = &hal.clock;
#if HAS_OTA
    ctx.halOta      = &hal.ota;
#endif
#if HAS_WIFI
    ctx.halWifi     = &hal.wifiManager;
#endif

    // Tier 1
    ctx.clock   = &clock;
    ctx.intents = &intents;
    ctx.bus     = &bus;
    ctx.mode    = &mode;
    ctx.gpio    = &gpio;
    ctx.pwm     = &pwm;

    // Tier 2
    ctx.dcMotor = &dcMotor;
    ctx.servo   = &servo;
    ctx.stepper = &stepper;
    ctx.motion  = &motion;

    // Tier 3
    ctx.encoder    = &encoder;
    ctx.imu        = &imu;
    ctx.lidar      = &lidar;
    ctx.ultrasonic = &ultrasonic;

    // Tier 4
    ctx.transport = &transport;
    ctx.uart      = uart;
    ctx.wifi      = wifi;
    ctx.ble       = ble;
    ctx.can       = can;
    ctx.router    = router;
    ctx.commands  = commands;
    ctx.telemetry = &telemetry;
    ctx.persistence = &persistence;

    // Tier 5
    ctx.control = control;
    ctx.host    = host;

    // Modules
    ctx.heartbeat = &heartbeat;
    ctx.logger    = &logger;
    ctx.identity  = identity;
#ifdef FEATURE_BENCHMARK
    ctx.benchmark = benchmarkModule;
#endif
    if (control) {
        ctx.observers = &control->observers();
    }

    // Handlers
    ctx.safetyHandler    = safetyHandler;
    ctx.motionHandler    = motionHandler;
    ctx.gpioHandler      = gpioHandler;
    ctx.servoHandler     = servoHandler;
    ctx.stepperHandler   = stepperHandler;
    ctx.dcMotorHandler   = dcMotorHandler;
    ctx.sensorHandler    = sensorHandler;
    ctx.telemetryHandler = telemetryHandler;
    ctx.controlHandler   = controlHandler;
    ctx.observerHandler  = observerHandler;

    // Schedulers
    ctx.safetyScheduler    = &safetyScheduler;
    ctx.controlScheduler   = &controlScheduler;
    ctx.telemetryScheduler = &telemetryScheduler;

    // Registries (singletons exposed via context for DI)
    ctx.handlerRegistry   = &HandlerRegistry::instance();
    ctx.moduleManager     = &ModuleManager::instance();
    ctx.sensorRegistry    = &SensorRegistry::instance();
    ctx.transportRegistry = &TransportRegistry::instance();
    ctx.actuatorRegistry  = &ActuatorRegistry::instance();

    return ctx;
}

} // namespace mara
