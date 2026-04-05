/**
 * @file mara_capi.h
 * @brief MARA Runtime C API for Python/ctypes Bindings
 *
 * This header provides a C-compatible interface to the MARA firmware runtime,
 * enabling control of Linux robots from Python via ctypes.
 *
 * Thread Safety:
 * - All functions are thread-safe (internal locking)
 * - Caller-provided buffers avoid memory ownership issues
 *
 * Error Handling:
 * - All functions return mara_error_t
 * - Use mara_error_string() to get human-readable error messages
 *
 * Usage:
 * @code
 *   mara_runtime_t rt;
 *   mara_create(&rt);
 *   mara_init(rt, "{}");  // JSON config
 *   mara_start(rt);
 *   mara_arm(rt);
 *
 *   mara_servo_write(rt, 0, 90.0f);
 *
 *   float ax, ay, az, gx, gy, gz;
 *   mara_imu_read(rt, &ax, &ay, &az, &gx, &gy, &gz);
 *
 *   mara_stop(rt);
 *   mara_destroy(rt);
 * @endcode
 */

#ifndef MARA_CAPI_H
#define MARA_CAPI_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =============================================================================
 * Types
 * =========================================================================== */

/** Opaque runtime handle */
typedef void* mara_runtime_t;

/** Error codes */
typedef enum {
    MARA_OK = 0,               /**< Success */
    MARA_ERR_INVALID_ARG,      /**< Invalid argument */
    MARA_ERR_INVALID_STATE,    /**< Invalid state for operation */
    MARA_ERR_NOT_INITIALIZED,  /**< Runtime not initialized */
    MARA_ERR_NOT_ARMED,        /**< Robot not armed */
    MARA_ERR_HARDWARE,         /**< Hardware error */
    MARA_ERR_TIMEOUT,          /**< Operation timed out */
    MARA_ERR_BUFFER_TOO_SMALL, /**< Buffer too small for response */
    MARA_ERR_NOT_SUPPORTED,    /**< Operation not supported */
    MARA_ERR_INTERNAL,         /**< Internal error */
} mara_error_t;

/** Robot state */
typedef enum {
    MARA_STATE_IDLE = 0,       /**< Idle - safe state */
    MARA_STATE_ARMED,          /**< Armed - ready for commands */
    MARA_STATE_ACTIVE,         /**< Active - executing commands */
    MARA_STATE_FAULT,          /**< Fault - error condition */
    MARA_STATE_UNKNOWN,        /**< Unknown state */
} mara_state_t;

/* =============================================================================
 * Lifecycle
 * =========================================================================== */

/**
 * @brief Create a new runtime instance
 *
 * @param out Pointer to receive runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_create(mara_runtime_t* out);

/**
 * @brief Initialize the runtime with configuration
 *
 * @param rt Runtime handle
 * @param config_json JSON configuration string (can be "{}" for defaults)
 * @return MARA_OK on success
 *
 * Configuration options:
 * - gpio_chip: GPIO chip path (default: "/dev/gpiochip0")
 * - i2c_bus: I2C bus number (default: 1)
 * - pwm_chip: PWM chip number (default: 0)
 * - log_level: Logging level ("trace", "debug", "info", "warn", "error")
 */
mara_error_t mara_init(mara_runtime_t rt, const char* config_json);

/**
 * @brief Start the runtime (begin hardware operations)
 *
 * @param rt Runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_start(mara_runtime_t rt);

/**
 * @brief Stop the runtime (halt hardware operations)
 *
 * @param rt Runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_stop(mara_runtime_t rt);

/**
 * @brief Destroy the runtime and free resources
 *
 * @param rt Runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_destroy(mara_runtime_t rt);

/* =============================================================================
 * State Machine
 * =========================================================================== */

/**
 * @brief Arm the robot (transition to ARMED state)
 *
 * @param rt Runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_arm(mara_runtime_t rt);

/**
 * @brief Disarm the robot (transition to IDLE state)
 *
 * @param rt Runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_disarm(mara_runtime_t rt);

/**
 * @brief Activate the robot (transition to ACTIVE state)
 *
 * @param rt Runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_activate(mara_runtime_t rt);

/**
 * @brief Deactivate the robot (transition from ACTIVE to ARMED)
 *
 * @param rt Runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_deactivate(mara_runtime_t rt);

/**
 * @brief Emergency stop
 *
 * @param rt Runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_estop(mara_runtime_t rt);

/**
 * @brief Clear emergency stop
 *
 * @param rt Runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_clear_estop(mara_runtime_t rt);

/**
 * @brief Get current robot state
 *
 * @param rt Runtime handle
 * @param state Pointer to receive state
 * @return MARA_OK on success
 */
mara_error_t mara_get_state(mara_runtime_t rt, mara_state_t* state);

/**
 * @brief Get current state as string
 *
 * @param rt Runtime handle
 * @param buf Buffer to receive state string
 * @param len Buffer length
 * @return MARA_OK on success
 */
mara_error_t mara_get_state_string(mara_runtime_t rt, char* buf, size_t len);

/* =============================================================================
 * GPIO Control
 * =========================================================================== */

/**
 * @brief Set GPIO pin mode
 *
 * @param rt Runtime handle
 * @param pin GPIO pin number
 * @param mode Pin mode: 0=Input, 1=Output, 2=InputPullup, 3=InputPulldown
 * @return MARA_OK on success
 */
mara_error_t mara_gpio_mode(mara_runtime_t rt, uint8_t pin, uint8_t mode);

/**
 * @brief Write digital value to GPIO pin
 *
 * @param rt Runtime handle
 * @param pin GPIO pin number
 * @param value 0 or 1
 * @return MARA_OK on success
 */
mara_error_t mara_gpio_write(mara_runtime_t rt, uint8_t pin, uint8_t value);

/**
 * @brief Read digital value from GPIO pin
 *
 * @param rt Runtime handle
 * @param pin GPIO pin number
 * @param value Pointer to receive value (0 or 1)
 * @return MARA_OK on success
 */
mara_error_t mara_gpio_read(mara_runtime_t rt, uint8_t pin, uint8_t* value);

/* =============================================================================
 * Servo Control
 * =========================================================================== */

/**
 * @brief Attach a servo to a pin
 *
 * @param rt Runtime handle
 * @param id Servo ID (0-15)
 * @param pin GPIO pin number
 * @param min_us Minimum pulse width (default: 500)
 * @param max_us Maximum pulse width (default: 2500)
 * @return MARA_OK on success
 */
mara_error_t mara_servo_attach(mara_runtime_t rt, uint8_t id, uint8_t pin,
                               uint16_t min_us, uint16_t max_us);

/**
 * @brief Detach a servo
 *
 * @param rt Runtime handle
 * @param id Servo ID
 * @return MARA_OK on success
 */
mara_error_t mara_servo_detach(mara_runtime_t rt, uint8_t id);

/**
 * @brief Write angle to servo
 *
 * @param rt Runtime handle
 * @param id Servo ID
 * @param angle Angle in degrees (0-180)
 * @return MARA_OK on success
 */
mara_error_t mara_servo_write(mara_runtime_t rt, uint8_t id, float angle);

/**
 * @brief Read current servo angle
 *
 * @param rt Runtime handle
 * @param id Servo ID
 * @param angle Pointer to receive angle
 * @return MARA_OK on success
 */
mara_error_t mara_servo_read(mara_runtime_t rt, uint8_t id, float* angle);

/* =============================================================================
 * Motor Control
 * =========================================================================== */

/**
 * @brief Set motor speed
 *
 * @param rt Runtime handle
 * @param id Motor ID
 * @param speed Speed (-100.0 to 100.0, percentage)
 * @return MARA_OK on success
 */
mara_error_t mara_motor_set(mara_runtime_t rt, uint8_t id, float speed);

/**
 * @brief Stop a motor
 *
 * @param rt Runtime handle
 * @param id Motor ID
 * @return MARA_OK on success
 */
mara_error_t mara_motor_stop(mara_runtime_t rt, uint8_t id);

/**
 * @brief Stop all motors
 *
 * @param rt Runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_motor_stop_all(mara_runtime_t rt);

/* =============================================================================
 * Motion Control
 * =========================================================================== */

/**
 * @brief Set robot velocity (differential drive)
 *
 * @param rt Runtime handle
 * @param vx Linear velocity (m/s)
 * @param omega Angular velocity (rad/s)
 * @return MARA_OK on success
 */
mara_error_t mara_set_velocity(mara_runtime_t rt, float vx, float omega);

/**
 * @brief Motion command - move forward
 *
 * @param rt Runtime handle
 * @param speed Speed percentage (0-100)
 * @return MARA_OK on success
 */
mara_error_t mara_motion_forward(mara_runtime_t rt, float speed);

/**
 * @brief Motion command - move backward
 *
 * @param rt Runtime handle
 * @param speed Speed percentage (0-100)
 * @return MARA_OK on success
 */
mara_error_t mara_motion_backward(mara_runtime_t rt, float speed);

/**
 * @brief Motion command - rotate left
 *
 * @param rt Runtime handle
 * @param speed Speed percentage (0-100)
 * @return MARA_OK on success
 */
mara_error_t mara_motion_rotate_left(mara_runtime_t rt, float speed);

/**
 * @brief Motion command - rotate right
 *
 * @param rt Runtime handle
 * @param speed Speed percentage (0-100)
 * @return MARA_OK on success
 */
mara_error_t mara_motion_rotate_right(mara_runtime_t rt, float speed);

/**
 * @brief Stop all motion
 *
 * @param rt Runtime handle
 * @return MARA_OK on success
 */
mara_error_t mara_stop_motion(mara_runtime_t rt);

/* =============================================================================
 * Sensors
 * =========================================================================== */

/**
 * @brief Read IMU data
 *
 * @param rt Runtime handle
 * @param ax Pointer to receive X acceleration (g)
 * @param ay Pointer to receive Y acceleration (g)
 * @param az Pointer to receive Z acceleration (g)
 * @param gx Pointer to receive X gyro (deg/s)
 * @param gy Pointer to receive Y gyro (deg/s)
 * @param gz Pointer to receive Z gyro (deg/s)
 * @return MARA_OK on success
 */
mara_error_t mara_imu_read(mara_runtime_t rt,
                           float* ax, float* ay, float* az,
                           float* gx, float* gy, float* gz);

/**
 * @brief Read encoder ticks
 *
 * @param rt Runtime handle
 * @param id Encoder ID
 * @param ticks Pointer to receive tick count
 * @return MARA_OK on success
 */
mara_error_t mara_encoder_read(mara_runtime_t rt, uint8_t id, int32_t* ticks);

/**
 * @brief Read ultrasonic distance
 *
 * @param rt Runtime handle
 * @param id Sensor ID
 * @param distance_cm Pointer to receive distance in cm
 * @return MARA_OK on success
 */
mara_error_t mara_ultrasonic_read(mara_runtime_t rt, uint8_t id, float* distance_cm);

/* =============================================================================
 * JSON Passthrough
 * =========================================================================== */

/**
 * @brief Execute a JSON command
 *
 * For complex commands not covered by the C API, use JSON passthrough.
 *
 * @param rt Runtime handle
 * @param cmd JSON command string
 * @param response Buffer to receive JSON response
 * @param len Response buffer length
 * @param actual Pointer to receive actual response length
 * @return MARA_OK on success
 */
mara_error_t mara_execute_json(mara_runtime_t rt, const char* cmd,
                               char* response, size_t len, size_t* actual);

/* =============================================================================
 * Identity and Diagnostics
 * =========================================================================== */

/**
 * @brief Get runtime identity/version info
 *
 * @param rt Runtime handle
 * @param info_json Buffer to receive JSON info
 * @param len Buffer length
 * @return MARA_OK on success
 */
mara_error_t mara_get_identity(mara_runtime_t rt, char* info_json, size_t len);

/**
 * @brief Get runtime health report
 *
 * @param rt Runtime handle
 * @param health_json Buffer to receive JSON health report
 * @param len Buffer length
 * @return MARA_OK on success
 */
mara_error_t mara_get_health(mara_runtime_t rt, char* health_json, size_t len);

/* =============================================================================
 * Utilities
 * =========================================================================== */

/**
 * @brief Get error string for error code
 *
 * @param err Error code
 * @return Human-readable error string
 */
const char* mara_error_string(mara_error_t err);

/**
 * @brief Get state string for state enum
 *
 * @param state State enum value
 * @return Human-readable state string
 */
const char* mara_state_string(mara_state_t state);

/**
 * @brief Get library version string
 *
 * @return Version string (e.g., "1.0.0")
 */
const char* mara_version(void);

#ifdef __cplusplus
}
#endif

#endif /* MARA_CAPI_H */
