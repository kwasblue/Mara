// include/sensor/SensorMacros.h
// Self-registration macro for sensors
//
// Usage:
//   class MySensor : public mara::ISensor {
//       // ... implementation
//   };
//   REGISTER_SENSOR(MySensor);

#pragma once

#include "sensor/SensorRegistry.h"

/// Register a sensor class with the global registry
/// Creates a static instance and registers it before main() runs
#define REGISTER_SENSOR(ClassName) \
    static ClassName __sensor_instance_##ClassName; \
    static struct __sensor_registrar_##ClassName { \
        __sensor_registrar_##ClassName() { \
            mara::SensorRegistry::instance().registerSensor(&__sensor_instance_##ClassName); \
        } \
    } __sensor_registrar_obj_##ClassName
