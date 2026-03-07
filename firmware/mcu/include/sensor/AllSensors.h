// include/sensor/AllSensors.h
// Include all self-registering sensors
//
// Add new sensors here for automatic registration.
// Sensors are conditionally compiled based on feature flags.

#pragma once

// Core infrastructure
#include "sensor/SensorRegistry.h"

// Self-registering sensors
#include "sensor/UltrasonicSensor.h"

// Future sensors:
// #include "sensor/ImuSensor.h"
// #include "sensor/EncoderSensor.h"
// #include "sensor/LidarSensor.h"
// #include "sensor/TempSensor.h"
