/**
 * @file mara_capi.cpp
 * @brief MARA Runtime C API Implementation
 */

#include "api/mara_capi.h"
#include "hal/PlatformHal.h"

#include <mutex>
#include <atomic>
#include <cstring>
#include <cstdio>

// Version info
#define MARA_VERSION_MAJOR 1
#define MARA_VERSION_MINOR 0
#define MARA_VERSION_PATCH 0
#define MARA_VERSION_STRING "1.0.0"

namespace {

/**
 * Runtime instance - wraps HAL and state machine
 */
struct MaraRuntimeImpl {
    hal::PlatformHalStorage halStorage;
    hal::HalContext hal;
    std::mutex mutex;
    std::atomic<bool> initialized{false};
    std::atomic<bool> started{false};
    std::atomic<mara_state_t> state{MARA_STATE_IDLE};

    MaraRuntimeImpl() : hal(halStorage.buildContext()) {}
};

// Helper to get impl from handle
inline MaraRuntimeImpl* getImpl(mara_runtime_t rt) {
    return reinterpret_cast<MaraRuntimeImpl*>(rt);
}

// State string table
const char* stateStrings[] = {
    "IDLE",
    "ARMED",
    "ACTIVE",
    "FAULT",
    "UNKNOWN"
};

// Error string table
const char* errorStrings[] = {
    "Success",
    "Invalid argument",
    "Invalid state for operation",
    "Runtime not initialized",
    "Robot not armed",
    "Hardware error",
    "Operation timed out",
    "Buffer too small",
    "Operation not supported",
    "Internal error"
};

} // anonymous namespace

/* =============================================================================
 * Lifecycle
 * =========================================================================== */

mara_error_t mara_create(mara_runtime_t* out) {
    if (!out) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = new (std::nothrow) MaraRuntimeImpl();
    if (!impl) {
        return MARA_ERR_INTERNAL;
    }

    *out = reinterpret_cast<mara_runtime_t>(impl);
    return MARA_OK;
}

mara_error_t mara_init(mara_runtime_t rt, const char* config_json) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    std::lock_guard<std::mutex> lock(impl->mutex);

    if (impl->initialized) {
        return MARA_OK;  // Already initialized
    }

    // Parse config JSON (simplified - just log level for now)
    if (config_json && strlen(config_json) > 2) {
        // TODO: Parse JSON config and apply settings
        // For now, use defaults
    }

    // Initialize HAL components
#if PLATFORM_LINUX
    if (!impl->halStorage.begin()) {
        return MARA_ERR_HARDWARE;
    }
#endif

    impl->initialized = true;
    impl->state = MARA_STATE_IDLE;

    return MARA_OK;
}

mara_error_t mara_start(mara_runtime_t rt) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    std::lock_guard<std::mutex> lock(impl->mutex);

    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    if (impl->started) {
        return MARA_OK;  // Already started
    }

    // Start any background tasks
    // TODO: Start control loops, telemetry, etc.

    impl->started = true;
    impl->hal.logger->info("MARA runtime started");

    return MARA_OK;
}

mara_error_t mara_stop(mara_runtime_t rt) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    std::lock_guard<std::mutex> lock(impl->mutex);

    if (!impl->started) {
        return MARA_OK;  // Already stopped
    }

    // Stop all motors first
    // TODO: Stop motors, servos, etc.

    impl->started = false;
    impl->state = MARA_STATE_IDLE;
    impl->hal.logger->info("MARA runtime stopped");

    return MARA_OK;
}

mara_error_t mara_destroy(mara_runtime_t rt) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);

    // Stop first if running
    mara_stop(rt);

    {
        std::lock_guard<std::mutex> lock(impl->mutex);
#if PLATFORM_LINUX
        impl->halStorage.end();
#endif
    }

    delete impl;
    return MARA_OK;
}

/* =============================================================================
 * State Machine
 * =========================================================================== */

mara_error_t mara_arm(mara_runtime_t rt) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    std::lock_guard<std::mutex> lock(impl->mutex);

    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    mara_state_t current = impl->state.load();
    if (current != MARA_STATE_IDLE) {
        return MARA_ERR_INVALID_STATE;
    }

    impl->state = MARA_STATE_ARMED;
    impl->hal.logger->info("Robot armed");

    return MARA_OK;
}

mara_error_t mara_disarm(mara_runtime_t rt) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    std::lock_guard<std::mutex> lock(impl->mutex);

    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    // Stop all actuators first
    // TODO: Stop motors, servos

    impl->state = MARA_STATE_IDLE;
    impl->hal.logger->info("Robot disarmed");

    return MARA_OK;
}

mara_error_t mara_activate(mara_runtime_t rt) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    std::lock_guard<std::mutex> lock(impl->mutex);

    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    mara_state_t current = impl->state.load();
    if (current != MARA_STATE_ARMED) {
        return MARA_ERR_INVALID_STATE;
    }

    impl->state = MARA_STATE_ACTIVE;
    impl->hal.logger->info("Robot activated");

    return MARA_OK;
}

mara_error_t mara_deactivate(mara_runtime_t rt) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    std::lock_guard<std::mutex> lock(impl->mutex);

    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    mara_state_t current = impl->state.load();
    if (current != MARA_STATE_ACTIVE) {
        return MARA_ERR_INVALID_STATE;
    }

    impl->state = MARA_STATE_ARMED;
    impl->hal.logger->info("Robot deactivated");

    return MARA_OK;
}

mara_error_t mara_estop(mara_runtime_t rt) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    // state is std::atomic — write is safe without the mutex.
    // We intentionally do not hold the mutex here so estop cannot
    // be blocked by another operation that already holds it.
    impl->state.store(MARA_STATE_FAULT);
    impl->hal.logger->warn("EMERGENCY STOP");

    // TODO: Stop all actuators immediately

    return MARA_OK;
}

mara_error_t mara_clear_estop(mara_runtime_t rt) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    std::lock_guard<std::mutex> lock(impl->mutex);

    if (impl->state.load() != MARA_STATE_FAULT) {
        return MARA_OK;  // Not in fault state
    }

    impl->state = MARA_STATE_IDLE;
    impl->hal.logger->info("E-stop cleared");

    return MARA_OK;
}

mara_error_t mara_get_state(mara_runtime_t rt, mara_state_t* state) {
    if (!rt || !state) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    *state = impl->state.load();

    return MARA_OK;
}

mara_error_t mara_get_state_string(mara_runtime_t rt, char* buf, size_t len) {
    if (!rt || !buf || len == 0) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    mara_state_t state = impl->state.load();

    const char* str = mara_state_string(state);
    size_t strLen = strlen(str);

    if (strLen >= len) {
        return MARA_ERR_BUFFER_TOO_SMALL;
    }

    memcpy(buf, str, strLen + 1);
    return MARA_OK;
}

/* =============================================================================
 * GPIO Control
 * =========================================================================== */

mara_error_t mara_gpio_mode(mara_runtime_t rt, uint8_t pin, uint8_t mode) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    hal::PinMode halMode;
    switch (mode) {
        case 0: halMode = hal::PinMode::Input; break;
        case 1: halMode = hal::PinMode::Output; break;
        case 2: halMode = hal::PinMode::InputPullup; break;
        case 3: halMode = hal::PinMode::InputPulldown; break;
        default: return MARA_ERR_INVALID_ARG;
    }

    impl->hal.gpio->pinMode(pin, halMode);
    return MARA_OK;
}

mara_error_t mara_gpio_write(mara_runtime_t rt, uint8_t pin, uint8_t value) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    impl->hal.gpio->digitalWrite(pin, value ? 1 : 0);
    return MARA_OK;
}

mara_error_t mara_gpio_read(mara_runtime_t rt, uint8_t pin, uint8_t* value) {
    if (!rt || !value) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    *value = impl->hal.gpio->digitalRead(pin) ? 1 : 0;
    return MARA_OK;
}

/* =============================================================================
 * Servo Control
 * =========================================================================== */

mara_error_t mara_servo_attach(mara_runtime_t rt, uint8_t id, uint8_t pin,
                               uint16_t min_us, uint16_t max_us) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    if (!impl->hal.servo->attach(id, pin, min_us, max_us)) {
        return MARA_ERR_HARDWARE;
    }

    return MARA_OK;
}

mara_error_t mara_servo_detach(mara_runtime_t rt, uint8_t id) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    impl->hal.servo->detach(id);
    return MARA_OK;
}

mara_error_t mara_servo_write(mara_runtime_t rt, uint8_t id, float angle) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    // Require armed state for actuator commands
    mara_state_t state = impl->state.load();
    if (state != MARA_STATE_ARMED && state != MARA_STATE_ACTIVE) {
        return MARA_ERR_NOT_ARMED;
    }

    impl->hal.servo->write(id, angle);
    return MARA_OK;
}

mara_error_t mara_servo_read(mara_runtime_t rt, uint8_t id, float* angle) {
    if (!rt || !angle) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    *angle = impl->hal.servo->read(id);
    return MARA_OK;
}

/* =============================================================================
 * Motor Control
 * =========================================================================== */

mara_error_t mara_motor_set(mara_runtime_t rt, uint8_t id, float speed) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    // Require armed state for actuator commands
    mara_state_t state = impl->state.load();
    if (state != MARA_STATE_ARMED && state != MARA_STATE_ACTIVE) {
        return MARA_ERR_NOT_ARMED;
    }

    // TODO: Implement motor control via PWM
    // impl->hal.pwm->setDuty(id, speed / 100.0f);
    (void)id;
    (void)speed;

    return MARA_ERR_NOT_SUPPORTED;
}

mara_error_t mara_motor_stop(mara_runtime_t rt, uint8_t id) {
    return mara_motor_set(rt, id, 0.0f);
}

mara_error_t mara_motor_stop_all(mara_runtime_t rt) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    // Stop all motors (0-7)
    for (uint8_t i = 0; i < 8; i++) {
        mara_motor_stop(rt, i);
    }

    return MARA_OK;
}

/* =============================================================================
 * Motion Control
 * =========================================================================== */

mara_error_t mara_set_velocity(mara_runtime_t rt, float vx, float omega) {
    if (!rt) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    // Require armed state for actuator commands
    mara_state_t state = impl->state.load();
    if (state != MARA_STATE_ARMED && state != MARA_STATE_ACTIVE) {
        return MARA_ERR_NOT_ARMED;
    }

    // TODO: Implement differential drive kinematics
    (void)vx;
    (void)omega;

    return MARA_ERR_NOT_SUPPORTED;
}

mara_error_t mara_motion_forward(mara_runtime_t rt, float speed) {
    return mara_set_velocity(rt, speed / 100.0f, 0.0f);
}

mara_error_t mara_motion_backward(mara_runtime_t rt, float speed) {
    return mara_set_velocity(rt, -speed / 100.0f, 0.0f);
}

mara_error_t mara_motion_rotate_left(mara_runtime_t rt, float speed) {
    return mara_set_velocity(rt, 0.0f, speed / 100.0f);
}

mara_error_t mara_motion_rotate_right(mara_runtime_t rt, float speed) {
    return mara_set_velocity(rt, 0.0f, -speed / 100.0f);
}

mara_error_t mara_stop_motion(mara_runtime_t rt) {
    return mara_set_velocity(rt, 0.0f, 0.0f);
}

/* =============================================================================
 * Sensors
 * =========================================================================== */

mara_error_t mara_imu_read(mara_runtime_t rt,
                           float* ax, float* ay, float* az,
                           float* gx, float* gy, float* gz) {
    if (!rt || !ax || !ay || !az || !gx || !gy || !gz) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    // IMU not yet implemented for Linux — no I2C IMU driver
    (void)ax; (void)ay; (void)az;
    (void)gx; (void)gy; (void)gz;

    return MARA_ERR_NOT_SUPPORTED;
}

mara_error_t mara_encoder_read(mara_runtime_t rt, uint8_t id, int32_t* ticks) {
    if (!rt || !ticks) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    // TODO: Implement encoder reading
    (void)id;
    *ticks = 0;

    return MARA_ERR_NOT_SUPPORTED;
}

mara_error_t mara_ultrasonic_read(mara_runtime_t rt, uint8_t id, float* distance_cm) {
    if (!rt || !distance_cm) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    // TODO: Implement ultrasonic reading
    (void)id;
    *distance_cm = 0.0f;

    return MARA_ERR_NOT_SUPPORTED;
}

/* =============================================================================
 * JSON Passthrough
 * =========================================================================== */

mara_error_t mara_execute_json(mara_runtime_t rt, const char* cmd,
                               char* response, size_t len, size_t* actual) {
    if (!rt || !cmd || !response || len == 0) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);
    if (!impl->initialized) {
        return MARA_ERR_NOT_INITIALIZED;
    }

    // TODO: Implement JSON command parsing
    // For now, return error response
    const char* resp = "{\"error\": \"not_implemented\"}";
    size_t respLen = strlen(resp);

    if (respLen >= len) {
        return MARA_ERR_BUFFER_TOO_SMALL;
    }

    memcpy(response, resp, respLen + 1);
    if (actual) {
        *actual = respLen;
    }

    return MARA_ERR_NOT_SUPPORTED;
}

/* =============================================================================
 * Identity and Diagnostics
 * =========================================================================== */

mara_error_t mara_get_identity(mara_runtime_t rt, char* info_json, size_t len) {
    if (!rt || !info_json || len == 0) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);

    char buf[256];
    int written = snprintf(buf, sizeof(buf),
        "{"
        "\"version\":\"%s\","
        "\"platform\":\"linux\","
        "\"initialized\":%s,"
        "\"started\":%s,"
        "\"state\":\"%s\""
        "}",
        MARA_VERSION_STRING,
        impl->initialized ? "true" : "false",
        impl->started ? "true" : "false",
        mara_state_string(impl->state.load())
    );

    if (written < 0 || written >= static_cast<int>(sizeof(buf)) ||
        static_cast<size_t>(written) >= len) {
        return MARA_ERR_BUFFER_TOO_SMALL;
    }

    memcpy(info_json, buf, written + 1);
    return MARA_OK;
}

mara_error_t mara_get_health(mara_runtime_t rt, char* health_json, size_t len) {
    if (!rt || !health_json || len == 0) {
        return MARA_ERR_INVALID_ARG;
    }

    auto* impl = getImpl(rt);

    mara_state_t state = impl->state.load();
    bool healthy = impl->initialized && impl->started && state != MARA_STATE_FAULT;

    char buf[256];
    int written = snprintf(buf, sizeof(buf),
        "{"
        "\"healthy\":%s,"
        "\"state\":\"%s\","
        "\"uptime_ms\":%u"
        "}",
        healthy ? "true" : "false",
        mara_state_string(state),
        impl->hal.clock->millis()
    );

    if (written < 0 || written >= static_cast<int>(sizeof(buf)) ||
        static_cast<size_t>(written) >= len) {
        return MARA_ERR_BUFFER_TOO_SMALL;
    }

    memcpy(health_json, buf, written + 1);
    return MARA_OK;
}

/* =============================================================================
 * Utilities
 * =========================================================================== */

const char* mara_error_string(mara_error_t err) {
    if (err >= 0 && err <= MARA_ERR_INTERNAL) {
        return errorStrings[err];
    }
    return "Unknown error";
}

const char* mara_state_string(mara_state_t state) {
    if (state >= MARA_STATE_IDLE && state <= MARA_STATE_UNKNOWN) {
        return stateStrings[state];
    }
    return "UNKNOWN";
}

const char* mara_version(void) {
    return MARA_VERSION_STRING;
}
