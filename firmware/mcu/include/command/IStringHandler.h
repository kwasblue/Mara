// include/command/IStringHandler.h
// Modern handler interface with string-based dispatch for extensibility

#pragma once

#include <cstdint>
#include <ArduinoJson.h>

// Forward declaration
struct CommandContext;

/**
 * Handler capabilities bitmask.
 * Used to gate handler dispatch based on available hardware/features.
 * Maps to HAS_* feature flags in FeatureFlags.h.
 */
namespace HandlerCap {
    constexpr uint32_t NONE           = 0;

    // Transport
    constexpr uint32_t WIFI           = (1 << 0);
    constexpr uint32_t BLE            = (1 << 1);
    constexpr uint32_t MQTT           = (1 << 2);
    constexpr uint32_t CAN            = (1 << 17);

    // Motor
    constexpr uint32_t DC_MOTOR       = (1 << 3);
    constexpr uint32_t SERVO          = (1 << 4);
    constexpr uint32_t STEPPER        = (1 << 5);
    constexpr uint32_t MOTION_CTRL    = (1 << 6);

    // Sensor
    constexpr uint32_t ENCODER        = (1 << 7);
    constexpr uint32_t IMU            = (1 << 8);
    constexpr uint32_t LIDAR          = (1 << 9);
    constexpr uint32_t ULTRASONIC     = (1 << 10);

    // Control
    constexpr uint32_t SIGNAL_BUS     = (1 << 11);
    constexpr uint32_t CONTROL_KERNEL = (1 << 12);
    constexpr uint32_t OBSERVER       = (1 << 13);

    // System
    constexpr uint32_t TELEMETRY      = (1 << 14);
    constexpr uint32_t SAFETY         = (1 << 15);

    // Audio
    constexpr uint32_t AUDIO          = (1 << 16);
}

/**
 * Interface for string-based command handlers.
 *
 * This interface enables self-registration of handlers via static constructors,
 * eliminating the need to manually update multiple files when adding a new handler.
 *
 * To add a new handler:
 * 1. Create a class that inherits from IStringHandler
 * 2. Define a static CMDS[] array with command strings
 * 3. Implement commands(), name(), and handle()
 * 4. Use REGISTER_HANDLER(ClassName) macro at the end of the file
 *
 * Example:
 *   class MyHandler : public IStringHandler {
 *   public:
 *       static constexpr const char* CMDS[] = {"CMD_FOO", "CMD_BAR", nullptr};
 *       const char* const* commands() const override { return CMDS; }
 *       const char* name() const override { return "MyHandler"; }
 *       void handle(const char* cmd, JsonVariantConst payload, CommandContext& ctx) override;
 *   };
 *   REGISTER_HANDLER(MyHandler);
 */
class IStringHandler {
public:
    virtual ~IStringHandler() = default;

    /**
     * Get null-terminated array of command strings this handler supports.
     * Example: {"CMD_FOO", "CMD_BAR", nullptr}
     */
    virtual const char* const* commands() const = 0;

    /**
     * Handle a command by string name.
     * @param cmd The command string (e.g., "CMD_SET_VEL")
     * @param payload JSON payload with command parameters
     * @param ctx Context for sending ACKs/errors and accessing shared state
     */
    virtual void handle(const char* cmd, JsonVariantConst payload, CommandContext& ctx) = 0;

    /**
     * Get handler name for debugging.
     */
    virtual const char* name() const = 0;

    /**
     * Get handler priority (lower = earlier in dispatch order).
     * Default is 100. Safety-critical handlers should use < 50.
     */
    virtual int priority() const { return 100; }

    /**
     * Get required capabilities bitmask.
     * Handler will only be dispatched if all required caps are available.
     * Default is NONE (no requirements).
     * @see HandlerCap namespace for available capability bits
     */
    virtual uint32_t requiredCaps() const { return HandlerCap::NONE; }
};
