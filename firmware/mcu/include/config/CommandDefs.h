// AUTO-GENERATED FILE — DO NOT EDIT BY HAND
// Generated from COMMANDS in schema.py

#pragma once
#include <string>
#include <unordered_map>

enum class CmdType {
    ACTIVATE,
    ARM,
    BATCH_APPLY,
    CAM_APPLY_PRESET,
    CAM_CAPTURE_FRAME,
    CAM_FLASH,
    CAM_GET_CONFIG,
    CAM_GET_STATUS,
    CAM_SET_AWB,
    CAM_SET_BRIGHTNESS,
    CAM_SET_CONTRAST,
    CAM_SET_EXPOSURE,
    CAM_SET_FLIP,
    CAM_SET_GAIN,
    CAM_SET_MOTION_DETECTION,
    CAM_SET_QUALITY,
    CAM_SET_RESOLUTION,
    CAM_SET_SATURATION,
    CAM_SET_SHARPNESS,
    CAM_START_CAPTURE,
    CAM_START_RECORDING,
    CAM_STOP_CAPTURE,
    CAM_STOP_RECORDING,
    CLEAR_ESTOP,
    CLEAR_SUBSYSTEM_LOG_LEVELS,
    CTRL_GRAPH_CLEAR,
    CTRL_GRAPH_ENABLE,
    CTRL_GRAPH_STATUS,
    CTRL_GRAPH_UPLOAD,
    CTRL_SET_RATE,
    CTRL_SIGNALS_CLEAR,
    CTRL_SIGNALS_LIST,
    CTRL_SIGNAL_DEFINE,
    CTRL_SIGNAL_DELETE,
    CTRL_SIGNAL_GET,
    CTRL_SIGNAL_SET,
    CTRL_SLOT_CONFIG,
    CTRL_SLOT_ENABLE,
    CTRL_SLOT_GET_PARAM,
    CTRL_SLOT_RESET,
    CTRL_SLOT_SET_PARAM,
    CTRL_SLOT_SET_PARAM_ARRAY,
    CTRL_SLOT_STATUS,
    DC_SET_SPEED,
    DC_SET_VEL_GAINS,
    DC_SET_VEL_TARGET,
    DC_STOP,
    DC_VEL_PID_ENABLE,
    DEACTIVATE,
    DISARM,
    ENCODER_ATTACH,
    ENCODER_DETACH,
    ENCODER_READ,
    ENCODER_RESET,
    ESTOP,
    GET_IDENTITY,
    GET_LOG_LEVELS,
    GET_RATES,
    GET_SAFETY_TIMEOUTS,
    GET_STATE,
    GPIO_READ,
    GPIO_REGISTER_CHANNEL,
    GPIO_TOGGLE,
    GPIO_WRITE,
    HEARTBEAT,
    I2C_SCAN,
    IMU_CALIBRATE,
    IMU_READ,
    IMU_SET_BIAS,
    IMU_ZERO,
    LED_OFF,
    LED_ON,
    MCU_DIAGNOSTICS_QUERY,
    MCU_DIAGNOSTICS_RESET,
    OBSERVER_CONFIG,
    OBSERVER_ENABLE,
    OBSERVER_RESET,
    OBSERVER_SET_PARAM,
    OBSERVER_SET_PARAM_ARRAY,
    OBSERVER_STATUS,
    PWM_SET,
    SAFETY_SET_RATE,
    SERVO_ATTACH,
    SERVO_DETACH,
    SERVO_SET_ANGLE,
    SERVO_SET_PULSE,
    SET_LOG_LEVEL,
    SET_MODE,
    SET_SAFETY_TIMEOUTS,
    SET_SUBSYSTEM_LOG_LEVEL,
    SET_VEL,
    STEPPER_ENABLE,
    STEPPER_GET_POSITION,
    STEPPER_MOVE_DEG,
    STEPPER_MOVE_REL,
    STEPPER_MOVE_REV,
    STEPPER_RESET_POSITION,
    STEPPER_STOP,
    STOP,
    TELEM_SET_INTERVAL,
    TELEM_SET_RATE,
    ULTRASONIC_ATTACH,
    ULTRASONIC_DETACH,
    ULTRASONIC_READ,
    WIFI_DISCONNECT,
    WIFI_JOIN,
    WIFI_SCAN,
    WIFI_STATUS,
    UNKNOWN
};

// Optimized O(1) lookup using hash map instead of O(n) if-else chain
inline CmdType cmdTypeFromString(const std::string& s) {
    static const std::unordered_map<std::string, CmdType> CMD_MAP = {
        {"CMD_ACTIVATE", CmdType::ACTIVATE},
        {"CMD_ARM", CmdType::ARM},
        {"CMD_BATCH_APPLY", CmdType::BATCH_APPLY},
        {"CMD_CAM_APPLY_PRESET", CmdType::CAM_APPLY_PRESET},
        {"CMD_CAM_CAPTURE_FRAME", CmdType::CAM_CAPTURE_FRAME},
        {"CMD_CAM_FLASH", CmdType::CAM_FLASH},
        {"CMD_CAM_GET_CONFIG", CmdType::CAM_GET_CONFIG},
        {"CMD_CAM_GET_STATUS", CmdType::CAM_GET_STATUS},
        {"CMD_CAM_SET_AWB", CmdType::CAM_SET_AWB},
        {"CMD_CAM_SET_BRIGHTNESS", CmdType::CAM_SET_BRIGHTNESS},
        {"CMD_CAM_SET_CONTRAST", CmdType::CAM_SET_CONTRAST},
        {"CMD_CAM_SET_EXPOSURE", CmdType::CAM_SET_EXPOSURE},
        {"CMD_CAM_SET_FLIP", CmdType::CAM_SET_FLIP},
        {"CMD_CAM_SET_GAIN", CmdType::CAM_SET_GAIN},
        {"CMD_CAM_SET_MOTION_DETECTION", CmdType::CAM_SET_MOTION_DETECTION},
        {"CMD_CAM_SET_QUALITY", CmdType::CAM_SET_QUALITY},
        {"CMD_CAM_SET_RESOLUTION", CmdType::CAM_SET_RESOLUTION},
        {"CMD_CAM_SET_SATURATION", CmdType::CAM_SET_SATURATION},
        {"CMD_CAM_SET_SHARPNESS", CmdType::CAM_SET_SHARPNESS},
        {"CMD_CAM_START_CAPTURE", CmdType::CAM_START_CAPTURE},
        {"CMD_CAM_START_RECORDING", CmdType::CAM_START_RECORDING},
        {"CMD_CAM_STOP_CAPTURE", CmdType::CAM_STOP_CAPTURE},
        {"CMD_CAM_STOP_RECORDING", CmdType::CAM_STOP_RECORDING},
        {"CMD_CLEAR_ESTOP", CmdType::CLEAR_ESTOP},
        {"CMD_CLEAR_SUBSYSTEM_LOG_LEVELS", CmdType::CLEAR_SUBSYSTEM_LOG_LEVELS},
        {"CMD_CTRL_GRAPH_CLEAR", CmdType::CTRL_GRAPH_CLEAR},
        {"CMD_CTRL_GRAPH_ENABLE", CmdType::CTRL_GRAPH_ENABLE},
        {"CMD_CTRL_GRAPH_STATUS", CmdType::CTRL_GRAPH_STATUS},
        {"CMD_CTRL_GRAPH_UPLOAD", CmdType::CTRL_GRAPH_UPLOAD},
        {"CMD_CTRL_SET_RATE", CmdType::CTRL_SET_RATE},
        {"CMD_CTRL_SIGNALS_CLEAR", CmdType::CTRL_SIGNALS_CLEAR},
        {"CMD_CTRL_SIGNALS_LIST", CmdType::CTRL_SIGNALS_LIST},
        {"CMD_CTRL_SIGNAL_DEFINE", CmdType::CTRL_SIGNAL_DEFINE},
        {"CMD_CTRL_SIGNAL_DELETE", CmdType::CTRL_SIGNAL_DELETE},
        {"CMD_CTRL_SIGNAL_GET", CmdType::CTRL_SIGNAL_GET},
        {"CMD_CTRL_SIGNAL_SET", CmdType::CTRL_SIGNAL_SET},
        {"CMD_CTRL_SLOT_CONFIG", CmdType::CTRL_SLOT_CONFIG},
        {"CMD_CTRL_SLOT_ENABLE", CmdType::CTRL_SLOT_ENABLE},
        {"CMD_CTRL_SLOT_GET_PARAM", CmdType::CTRL_SLOT_GET_PARAM},
        {"CMD_CTRL_SLOT_RESET", CmdType::CTRL_SLOT_RESET},
        {"CMD_CTRL_SLOT_SET_PARAM", CmdType::CTRL_SLOT_SET_PARAM},
        {"CMD_CTRL_SLOT_SET_PARAM_ARRAY", CmdType::CTRL_SLOT_SET_PARAM_ARRAY},
        {"CMD_CTRL_SLOT_STATUS", CmdType::CTRL_SLOT_STATUS},
        {"CMD_DC_SET_SPEED", CmdType::DC_SET_SPEED},
        {"CMD_DC_SET_VEL_GAINS", CmdType::DC_SET_VEL_GAINS},
        {"CMD_DC_SET_VEL_TARGET", CmdType::DC_SET_VEL_TARGET},
        {"CMD_DC_STOP", CmdType::DC_STOP},
        {"CMD_DC_VEL_PID_ENABLE", CmdType::DC_VEL_PID_ENABLE},
        {"CMD_DEACTIVATE", CmdType::DEACTIVATE},
        {"CMD_DISARM", CmdType::DISARM},
        {"CMD_ENCODER_ATTACH", CmdType::ENCODER_ATTACH},
        {"CMD_ENCODER_DETACH", CmdType::ENCODER_DETACH},
        {"CMD_ENCODER_READ", CmdType::ENCODER_READ},
        {"CMD_ENCODER_RESET", CmdType::ENCODER_RESET},
        {"CMD_ESTOP", CmdType::ESTOP},
        {"CMD_GET_IDENTITY", CmdType::GET_IDENTITY},
        {"CMD_GET_LOG_LEVELS", CmdType::GET_LOG_LEVELS},
        {"CMD_GET_RATES", CmdType::GET_RATES},
        {"CMD_GET_SAFETY_TIMEOUTS", CmdType::GET_SAFETY_TIMEOUTS},
        {"CMD_GET_STATE", CmdType::GET_STATE},
        {"CMD_GPIO_READ", CmdType::GPIO_READ},
        {"CMD_GPIO_REGISTER_CHANNEL", CmdType::GPIO_REGISTER_CHANNEL},
        {"CMD_GPIO_TOGGLE", CmdType::GPIO_TOGGLE},
        {"CMD_GPIO_WRITE", CmdType::GPIO_WRITE},
        {"CMD_HEARTBEAT", CmdType::HEARTBEAT},
        {"CMD_I2C_SCAN", CmdType::I2C_SCAN},
        {"CMD_IMU_CALIBRATE", CmdType::IMU_CALIBRATE},
        {"CMD_IMU_READ", CmdType::IMU_READ},
        {"CMD_IMU_SET_BIAS", CmdType::IMU_SET_BIAS},
        {"CMD_IMU_ZERO", CmdType::IMU_ZERO},
        {"CMD_LED_OFF", CmdType::LED_OFF},
        {"CMD_LED_ON", CmdType::LED_ON},
        {"CMD_MCU_DIAGNOSTICS_QUERY", CmdType::MCU_DIAGNOSTICS_QUERY},
        {"CMD_MCU_DIAGNOSTICS_RESET", CmdType::MCU_DIAGNOSTICS_RESET},
        {"CMD_OBSERVER_CONFIG", CmdType::OBSERVER_CONFIG},
        {"CMD_OBSERVER_ENABLE", CmdType::OBSERVER_ENABLE},
        {"CMD_OBSERVER_RESET", CmdType::OBSERVER_RESET},
        {"CMD_OBSERVER_SET_PARAM", CmdType::OBSERVER_SET_PARAM},
        {"CMD_OBSERVER_SET_PARAM_ARRAY", CmdType::OBSERVER_SET_PARAM_ARRAY},
        {"CMD_OBSERVER_STATUS", CmdType::OBSERVER_STATUS},
        {"CMD_PWM_SET", CmdType::PWM_SET},
        {"CMD_SAFETY_SET_RATE", CmdType::SAFETY_SET_RATE},
        {"CMD_SERVO_ATTACH", CmdType::SERVO_ATTACH},
        {"CMD_SERVO_DETACH", CmdType::SERVO_DETACH},
        {"CMD_SERVO_SET_ANGLE", CmdType::SERVO_SET_ANGLE},
        {"CMD_SERVO_SET_PULSE", CmdType::SERVO_SET_PULSE},
        {"CMD_SET_LOG_LEVEL", CmdType::SET_LOG_LEVEL},
        {"CMD_SET_MODE", CmdType::SET_MODE},
        {"CMD_SET_SAFETY_TIMEOUTS", CmdType::SET_SAFETY_TIMEOUTS},
        {"CMD_SET_SUBSYSTEM_LOG_LEVEL", CmdType::SET_SUBSYSTEM_LOG_LEVEL},
        {"CMD_SET_VEL", CmdType::SET_VEL},
        {"CMD_STEPPER_ENABLE", CmdType::STEPPER_ENABLE},
        {"CMD_STEPPER_GET_POSITION", CmdType::STEPPER_GET_POSITION},
        {"CMD_STEPPER_MOVE_DEG", CmdType::STEPPER_MOVE_DEG},
        {"CMD_STEPPER_MOVE_REL", CmdType::STEPPER_MOVE_REL},
        {"CMD_STEPPER_MOVE_REV", CmdType::STEPPER_MOVE_REV},
        {"CMD_STEPPER_RESET_POSITION", CmdType::STEPPER_RESET_POSITION},
        {"CMD_STEPPER_STOP", CmdType::STEPPER_STOP},
        {"CMD_STOP", CmdType::STOP},
        {"CMD_TELEM_SET_INTERVAL", CmdType::TELEM_SET_INTERVAL},
        {"CMD_TELEM_SET_RATE", CmdType::TELEM_SET_RATE},
        {"CMD_ULTRASONIC_ATTACH", CmdType::ULTRASONIC_ATTACH},
        {"CMD_ULTRASONIC_DETACH", CmdType::ULTRASONIC_DETACH},
        {"CMD_ULTRASONIC_READ", CmdType::ULTRASONIC_READ},
        {"CMD_WIFI_DISCONNECT", CmdType::WIFI_DISCONNECT},
        {"CMD_WIFI_JOIN", CmdType::WIFI_JOIN},
        {"CMD_WIFI_SCAN", CmdType::WIFI_SCAN},
        {"CMD_WIFI_STATUS", CmdType::WIFI_STATUS},
    };
    auto it = CMD_MAP.find(s);
    return (it != CMD_MAP.end()) ? it->second : CmdType::UNKNOWN;
}

inline const char* cmdTypeToString(CmdType c) {
    switch (c) {
        case CmdType::ACTIVATE: return "CMD_ACTIVATE";
        case CmdType::ARM: return "CMD_ARM";
        case CmdType::BATCH_APPLY: return "CMD_BATCH_APPLY";
        case CmdType::CAM_APPLY_PRESET: return "CMD_CAM_APPLY_PRESET";
        case CmdType::CAM_CAPTURE_FRAME: return "CMD_CAM_CAPTURE_FRAME";
        case CmdType::CAM_FLASH: return "CMD_CAM_FLASH";
        case CmdType::CAM_GET_CONFIG: return "CMD_CAM_GET_CONFIG";
        case CmdType::CAM_GET_STATUS: return "CMD_CAM_GET_STATUS";
        case CmdType::CAM_SET_AWB: return "CMD_CAM_SET_AWB";
        case CmdType::CAM_SET_BRIGHTNESS: return "CMD_CAM_SET_BRIGHTNESS";
        case CmdType::CAM_SET_CONTRAST: return "CMD_CAM_SET_CONTRAST";
        case CmdType::CAM_SET_EXPOSURE: return "CMD_CAM_SET_EXPOSURE";
        case CmdType::CAM_SET_FLIP: return "CMD_CAM_SET_FLIP";
        case CmdType::CAM_SET_GAIN: return "CMD_CAM_SET_GAIN";
        case CmdType::CAM_SET_MOTION_DETECTION: return "CMD_CAM_SET_MOTION_DETECTION";
        case CmdType::CAM_SET_QUALITY: return "CMD_CAM_SET_QUALITY";
        case CmdType::CAM_SET_RESOLUTION: return "CMD_CAM_SET_RESOLUTION";
        case CmdType::CAM_SET_SATURATION: return "CMD_CAM_SET_SATURATION";
        case CmdType::CAM_SET_SHARPNESS: return "CMD_CAM_SET_SHARPNESS";
        case CmdType::CAM_START_CAPTURE: return "CMD_CAM_START_CAPTURE";
        case CmdType::CAM_START_RECORDING: return "CMD_CAM_START_RECORDING";
        case CmdType::CAM_STOP_CAPTURE: return "CMD_CAM_STOP_CAPTURE";
        case CmdType::CAM_STOP_RECORDING: return "CMD_CAM_STOP_RECORDING";
        case CmdType::CLEAR_ESTOP: return "CMD_CLEAR_ESTOP";
        case CmdType::CLEAR_SUBSYSTEM_LOG_LEVELS: return "CMD_CLEAR_SUBSYSTEM_LOG_LEVELS";
        case CmdType::CTRL_GRAPH_CLEAR: return "CMD_CTRL_GRAPH_CLEAR";
        case CmdType::CTRL_GRAPH_ENABLE: return "CMD_CTRL_GRAPH_ENABLE";
        case CmdType::CTRL_GRAPH_STATUS: return "CMD_CTRL_GRAPH_STATUS";
        case CmdType::CTRL_GRAPH_UPLOAD: return "CMD_CTRL_GRAPH_UPLOAD";
        case CmdType::CTRL_SET_RATE: return "CMD_CTRL_SET_RATE";
        case CmdType::CTRL_SIGNALS_CLEAR: return "CMD_CTRL_SIGNALS_CLEAR";
        case CmdType::CTRL_SIGNALS_LIST: return "CMD_CTRL_SIGNALS_LIST";
        case CmdType::CTRL_SIGNAL_DEFINE: return "CMD_CTRL_SIGNAL_DEFINE";
        case CmdType::CTRL_SIGNAL_DELETE: return "CMD_CTRL_SIGNAL_DELETE";
        case CmdType::CTRL_SIGNAL_GET: return "CMD_CTRL_SIGNAL_GET";
        case CmdType::CTRL_SIGNAL_SET: return "CMD_CTRL_SIGNAL_SET";
        case CmdType::CTRL_SLOT_CONFIG: return "CMD_CTRL_SLOT_CONFIG";
        case CmdType::CTRL_SLOT_ENABLE: return "CMD_CTRL_SLOT_ENABLE";
        case CmdType::CTRL_SLOT_GET_PARAM: return "CMD_CTRL_SLOT_GET_PARAM";
        case CmdType::CTRL_SLOT_RESET: return "CMD_CTRL_SLOT_RESET";
        case CmdType::CTRL_SLOT_SET_PARAM: return "CMD_CTRL_SLOT_SET_PARAM";
        case CmdType::CTRL_SLOT_SET_PARAM_ARRAY: return "CMD_CTRL_SLOT_SET_PARAM_ARRAY";
        case CmdType::CTRL_SLOT_STATUS: return "CMD_CTRL_SLOT_STATUS";
        case CmdType::DC_SET_SPEED: return "CMD_DC_SET_SPEED";
        case CmdType::DC_SET_VEL_GAINS: return "CMD_DC_SET_VEL_GAINS";
        case CmdType::DC_SET_VEL_TARGET: return "CMD_DC_SET_VEL_TARGET";
        case CmdType::DC_STOP: return "CMD_DC_STOP";
        case CmdType::DC_VEL_PID_ENABLE: return "CMD_DC_VEL_PID_ENABLE";
        case CmdType::DEACTIVATE: return "CMD_DEACTIVATE";
        case CmdType::DISARM: return "CMD_DISARM";
        case CmdType::ENCODER_ATTACH: return "CMD_ENCODER_ATTACH";
        case CmdType::ENCODER_DETACH: return "CMD_ENCODER_DETACH";
        case CmdType::ENCODER_READ: return "CMD_ENCODER_READ";
        case CmdType::ENCODER_RESET: return "CMD_ENCODER_RESET";
        case CmdType::ESTOP: return "CMD_ESTOP";
        case CmdType::GET_IDENTITY: return "CMD_GET_IDENTITY";
        case CmdType::GET_LOG_LEVELS: return "CMD_GET_LOG_LEVELS";
        case CmdType::GET_RATES: return "CMD_GET_RATES";
        case CmdType::GET_SAFETY_TIMEOUTS: return "CMD_GET_SAFETY_TIMEOUTS";
        case CmdType::GET_STATE: return "CMD_GET_STATE";
        case CmdType::GPIO_READ: return "CMD_GPIO_READ";
        case CmdType::GPIO_REGISTER_CHANNEL: return "CMD_GPIO_REGISTER_CHANNEL";
        case CmdType::GPIO_TOGGLE: return "CMD_GPIO_TOGGLE";
        case CmdType::GPIO_WRITE: return "CMD_GPIO_WRITE";
        case CmdType::HEARTBEAT: return "CMD_HEARTBEAT";
        case CmdType::I2C_SCAN: return "CMD_I2C_SCAN";
        case CmdType::IMU_CALIBRATE: return "CMD_IMU_CALIBRATE";
        case CmdType::IMU_READ: return "CMD_IMU_READ";
        case CmdType::IMU_SET_BIAS: return "CMD_IMU_SET_BIAS";
        case CmdType::IMU_ZERO: return "CMD_IMU_ZERO";
        case CmdType::LED_OFF: return "CMD_LED_OFF";
        case CmdType::LED_ON: return "CMD_LED_ON";
        case CmdType::MCU_DIAGNOSTICS_QUERY: return "CMD_MCU_DIAGNOSTICS_QUERY";
        case CmdType::MCU_DIAGNOSTICS_RESET: return "CMD_MCU_DIAGNOSTICS_RESET";
        case CmdType::OBSERVER_CONFIG: return "CMD_OBSERVER_CONFIG";
        case CmdType::OBSERVER_ENABLE: return "CMD_OBSERVER_ENABLE";
        case CmdType::OBSERVER_RESET: return "CMD_OBSERVER_RESET";
        case CmdType::OBSERVER_SET_PARAM: return "CMD_OBSERVER_SET_PARAM";
        case CmdType::OBSERVER_SET_PARAM_ARRAY: return "CMD_OBSERVER_SET_PARAM_ARRAY";
        case CmdType::OBSERVER_STATUS: return "CMD_OBSERVER_STATUS";
        case CmdType::PWM_SET: return "CMD_PWM_SET";
        case CmdType::SAFETY_SET_RATE: return "CMD_SAFETY_SET_RATE";
        case CmdType::SERVO_ATTACH: return "CMD_SERVO_ATTACH";
        case CmdType::SERVO_DETACH: return "CMD_SERVO_DETACH";
        case CmdType::SERVO_SET_ANGLE: return "CMD_SERVO_SET_ANGLE";
        case CmdType::SERVO_SET_PULSE: return "CMD_SERVO_SET_PULSE";
        case CmdType::SET_LOG_LEVEL: return "CMD_SET_LOG_LEVEL";
        case CmdType::SET_MODE: return "CMD_SET_MODE";
        case CmdType::SET_SAFETY_TIMEOUTS: return "CMD_SET_SAFETY_TIMEOUTS";
        case CmdType::SET_SUBSYSTEM_LOG_LEVEL: return "CMD_SET_SUBSYSTEM_LOG_LEVEL";
        case CmdType::SET_VEL: return "CMD_SET_VEL";
        case CmdType::STEPPER_ENABLE: return "CMD_STEPPER_ENABLE";
        case CmdType::STEPPER_GET_POSITION: return "CMD_STEPPER_GET_POSITION";
        case CmdType::STEPPER_MOVE_DEG: return "CMD_STEPPER_MOVE_DEG";
        case CmdType::STEPPER_MOVE_REL: return "CMD_STEPPER_MOVE_REL";
        case CmdType::STEPPER_MOVE_REV: return "CMD_STEPPER_MOVE_REV";
        case CmdType::STEPPER_RESET_POSITION: return "CMD_STEPPER_RESET_POSITION";
        case CmdType::STEPPER_STOP: return "CMD_STEPPER_STOP";
        case CmdType::STOP: return "CMD_STOP";
        case CmdType::TELEM_SET_INTERVAL: return "CMD_TELEM_SET_INTERVAL";
        case CmdType::TELEM_SET_RATE: return "CMD_TELEM_SET_RATE";
        case CmdType::ULTRASONIC_ATTACH: return "CMD_ULTRASONIC_ATTACH";
        case CmdType::ULTRASONIC_DETACH: return "CMD_ULTRASONIC_DETACH";
        case CmdType::ULTRASONIC_READ: return "CMD_ULTRASONIC_READ";
        case CmdType::WIFI_DISCONNECT: return "CMD_WIFI_DISCONNECT";
        case CmdType::WIFI_JOIN: return "CMD_WIFI_JOIN";
        case CmdType::WIFI_SCAN: return "CMD_WIFI_SCAN";
        case CmdType::WIFI_STATUS: return "CMD_WIFI_STATUS";
        default: return "UNKNOWN";
    }
}
