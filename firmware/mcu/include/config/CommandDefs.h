// AUTO-GENERATED FILE — DO NOT EDIT BY HAND
// Generated from COMMANDS in platform_schema.py

#pragma once
#include <string>

enum class CmdType {
    ACTIVATE,
    ARM,
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
    ENCODER_READ,
    ENCODER_RESET,
    ESTOP,
    GET_IDENTITY,
    GET_RATES,
    GPIO_READ,
    GPIO_REGISTER_CHANNEL,
    GPIO_TOGGLE,
    GPIO_WRITE,
    HEARTBEAT,
    LED_OFF,
    LED_ON,
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
    SET_LOG_LEVEL,
    SET_MODE,
    SET_VEL,
    STEPPER_ENABLE,
    STEPPER_MOVE_REL,
    STEPPER_STOP,
    STOP,
    TELEM_SET_INTERVAL,
    TELEM_SET_RATE,
    ULTRASONIC_ATTACH,
    ULTRASONIC_READ,
    UNKNOWN
};

inline CmdType cmdTypeFromString(const std::string& s) {
    if (s == "CMD_ACTIVATE") return CmdType::ACTIVATE;
    if (s == "CMD_ARM") return CmdType::ARM;
    if (s == "CMD_CAM_APPLY_PRESET") return CmdType::CAM_APPLY_PRESET;
    if (s == "CMD_CAM_CAPTURE_FRAME") return CmdType::CAM_CAPTURE_FRAME;
    if (s == "CMD_CAM_FLASH") return CmdType::CAM_FLASH;
    if (s == "CMD_CAM_GET_CONFIG") return CmdType::CAM_GET_CONFIG;
    if (s == "CMD_CAM_GET_STATUS") return CmdType::CAM_GET_STATUS;
    if (s == "CMD_CAM_SET_AWB") return CmdType::CAM_SET_AWB;
    if (s == "CMD_CAM_SET_BRIGHTNESS") return CmdType::CAM_SET_BRIGHTNESS;
    if (s == "CMD_CAM_SET_CONTRAST") return CmdType::CAM_SET_CONTRAST;
    if (s == "CMD_CAM_SET_EXPOSURE") return CmdType::CAM_SET_EXPOSURE;
    if (s == "CMD_CAM_SET_FLIP") return CmdType::CAM_SET_FLIP;
    if (s == "CMD_CAM_SET_GAIN") return CmdType::CAM_SET_GAIN;
    if (s == "CMD_CAM_SET_MOTION_DETECTION") return CmdType::CAM_SET_MOTION_DETECTION;
    if (s == "CMD_CAM_SET_QUALITY") return CmdType::CAM_SET_QUALITY;
    if (s == "CMD_CAM_SET_RESOLUTION") return CmdType::CAM_SET_RESOLUTION;
    if (s == "CMD_CAM_SET_SATURATION") return CmdType::CAM_SET_SATURATION;
    if (s == "CMD_CAM_SET_SHARPNESS") return CmdType::CAM_SET_SHARPNESS;
    if (s == "CMD_CAM_START_CAPTURE") return CmdType::CAM_START_CAPTURE;
    if (s == "CMD_CAM_START_RECORDING") return CmdType::CAM_START_RECORDING;
    if (s == "CMD_CAM_STOP_CAPTURE") return CmdType::CAM_STOP_CAPTURE;
    if (s == "CMD_CAM_STOP_RECORDING") return CmdType::CAM_STOP_RECORDING;
    if (s == "CMD_CLEAR_ESTOP") return CmdType::CLEAR_ESTOP;
    if (s == "CMD_CTRL_SET_RATE") return CmdType::CTRL_SET_RATE;
    if (s == "CMD_CTRL_SIGNALS_CLEAR") return CmdType::CTRL_SIGNALS_CLEAR;
    if (s == "CMD_CTRL_SIGNALS_LIST") return CmdType::CTRL_SIGNALS_LIST;
    if (s == "CMD_CTRL_SIGNAL_DEFINE") return CmdType::CTRL_SIGNAL_DEFINE;
    if (s == "CMD_CTRL_SIGNAL_DELETE") return CmdType::CTRL_SIGNAL_DELETE;
    if (s == "CMD_CTRL_SIGNAL_GET") return CmdType::CTRL_SIGNAL_GET;
    if (s == "CMD_CTRL_SIGNAL_SET") return CmdType::CTRL_SIGNAL_SET;
    if (s == "CMD_CTRL_SLOT_CONFIG") return CmdType::CTRL_SLOT_CONFIG;
    if (s == "CMD_CTRL_SLOT_ENABLE") return CmdType::CTRL_SLOT_ENABLE;
    if (s == "CMD_CTRL_SLOT_GET_PARAM") return CmdType::CTRL_SLOT_GET_PARAM;
    if (s == "CMD_CTRL_SLOT_RESET") return CmdType::CTRL_SLOT_RESET;
    if (s == "CMD_CTRL_SLOT_SET_PARAM") return CmdType::CTRL_SLOT_SET_PARAM;
    if (s == "CMD_CTRL_SLOT_SET_PARAM_ARRAY") return CmdType::CTRL_SLOT_SET_PARAM_ARRAY;
    if (s == "CMD_CTRL_SLOT_STATUS") return CmdType::CTRL_SLOT_STATUS;
    if (s == "CMD_DC_SET_SPEED") return CmdType::DC_SET_SPEED;
    if (s == "CMD_DC_SET_VEL_GAINS") return CmdType::DC_SET_VEL_GAINS;
    if (s == "CMD_DC_SET_VEL_TARGET") return CmdType::DC_SET_VEL_TARGET;
    if (s == "CMD_DC_STOP") return CmdType::DC_STOP;
    if (s == "CMD_DC_VEL_PID_ENABLE") return CmdType::DC_VEL_PID_ENABLE;
    if (s == "CMD_DEACTIVATE") return CmdType::DEACTIVATE;
    if (s == "CMD_DISARM") return CmdType::DISARM;
    if (s == "CMD_ENCODER_ATTACH") return CmdType::ENCODER_ATTACH;
    if (s == "CMD_ENCODER_READ") return CmdType::ENCODER_READ;
    if (s == "CMD_ENCODER_RESET") return CmdType::ENCODER_RESET;
    if (s == "CMD_ESTOP") return CmdType::ESTOP;
    if (s == "CMD_GET_IDENTITY") return CmdType::GET_IDENTITY;
    if (s == "CMD_GET_RATES") return CmdType::GET_RATES;
    if (s == "CMD_GPIO_READ") return CmdType::GPIO_READ;
    if (s == "CMD_GPIO_REGISTER_CHANNEL") return CmdType::GPIO_REGISTER_CHANNEL;
    if (s == "CMD_GPIO_TOGGLE") return CmdType::GPIO_TOGGLE;
    if (s == "CMD_GPIO_WRITE") return CmdType::GPIO_WRITE;
    if (s == "CMD_HEARTBEAT") return CmdType::HEARTBEAT;
    if (s == "CMD_LED_OFF") return CmdType::LED_OFF;
    if (s == "CMD_LED_ON") return CmdType::LED_ON;
    if (s == "CMD_OBSERVER_CONFIG") return CmdType::OBSERVER_CONFIG;
    if (s == "CMD_OBSERVER_ENABLE") return CmdType::OBSERVER_ENABLE;
    if (s == "CMD_OBSERVER_RESET") return CmdType::OBSERVER_RESET;
    if (s == "CMD_OBSERVER_SET_PARAM") return CmdType::OBSERVER_SET_PARAM;
    if (s == "CMD_OBSERVER_SET_PARAM_ARRAY") return CmdType::OBSERVER_SET_PARAM_ARRAY;
    if (s == "CMD_OBSERVER_STATUS") return CmdType::OBSERVER_STATUS;
    if (s == "CMD_PWM_SET") return CmdType::PWM_SET;
    if (s == "CMD_SAFETY_SET_RATE") return CmdType::SAFETY_SET_RATE;
    if (s == "CMD_SERVO_ATTACH") return CmdType::SERVO_ATTACH;
    if (s == "CMD_SERVO_DETACH") return CmdType::SERVO_DETACH;
    if (s == "CMD_SERVO_SET_ANGLE") return CmdType::SERVO_SET_ANGLE;
    if (s == "CMD_SET_LOG_LEVEL") return CmdType::SET_LOG_LEVEL;
    if (s == "CMD_SET_MODE") return CmdType::SET_MODE;
    if (s == "CMD_SET_VEL") return CmdType::SET_VEL;
    if (s == "CMD_STEPPER_ENABLE") return CmdType::STEPPER_ENABLE;
    if (s == "CMD_STEPPER_MOVE_REL") return CmdType::STEPPER_MOVE_REL;
    if (s == "CMD_STEPPER_STOP") return CmdType::STEPPER_STOP;
    if (s == "CMD_STOP") return CmdType::STOP;
    if (s == "CMD_TELEM_SET_INTERVAL") return CmdType::TELEM_SET_INTERVAL;
    if (s == "CMD_TELEM_SET_RATE") return CmdType::TELEM_SET_RATE;
    if (s == "CMD_ULTRASONIC_ATTACH") return CmdType::ULTRASONIC_ATTACH;
    if (s == "CMD_ULTRASONIC_READ") return CmdType::ULTRASONIC_READ;
    return CmdType::UNKNOWN;
}

inline const char* cmdTypeToString(CmdType c) {
    switch (c) {
        case CmdType::ACTIVATE: return "CMD_ACTIVATE";
        case CmdType::ARM: return "CMD_ARM";
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
        case CmdType::ENCODER_READ: return "CMD_ENCODER_READ";
        case CmdType::ENCODER_RESET: return "CMD_ENCODER_RESET";
        case CmdType::ESTOP: return "CMD_ESTOP";
        case CmdType::GET_IDENTITY: return "CMD_GET_IDENTITY";
        case CmdType::GET_RATES: return "CMD_GET_RATES";
        case CmdType::GPIO_READ: return "CMD_GPIO_READ";
        case CmdType::GPIO_REGISTER_CHANNEL: return "CMD_GPIO_REGISTER_CHANNEL";
        case CmdType::GPIO_TOGGLE: return "CMD_GPIO_TOGGLE";
        case CmdType::GPIO_WRITE: return "CMD_GPIO_WRITE";
        case CmdType::HEARTBEAT: return "CMD_HEARTBEAT";
        case CmdType::LED_OFF: return "CMD_LED_OFF";
        case CmdType::LED_ON: return "CMD_LED_ON";
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
        case CmdType::SET_LOG_LEVEL: return "CMD_SET_LOG_LEVEL";
        case CmdType::SET_MODE: return "CMD_SET_MODE";
        case CmdType::SET_VEL: return "CMD_SET_VEL";
        case CmdType::STEPPER_ENABLE: return "CMD_STEPPER_ENABLE";
        case CmdType::STEPPER_MOVE_REL: return "CMD_STEPPER_MOVE_REL";
        case CmdType::STEPPER_STOP: return "CMD_STEPPER_STOP";
        case CmdType::STOP: return "CMD_STOP";
        case CmdType::TELEM_SET_INTERVAL: return "CMD_TELEM_SET_INTERVAL";
        case CmdType::TELEM_SET_RATE: return "CMD_TELEM_SET_RATE";
        case CmdType::ULTRASONIC_ATTACH: return "CMD_ULTRASONIC_ATTACH";
        case CmdType::ULTRASONIC_READ: return "CMD_ULTRASONIC_READ";
        default: return "UNKNOWN";
    }
}
