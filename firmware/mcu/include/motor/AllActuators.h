// include/motor/AllActuators.h
// Include all self-registering actuators
//
// Add new actuators here for automatic registration.
// Actuators are conditionally compiled based on feature flags.

#pragma once

// Core infrastructure
#include "motor/ActuatorRegistry.h"

// Self-registering actuators
#include "motor/DcMotorActuator.h"

// Future actuators (migrate from legacy managers):
// #include "motor/ServoActuator.h"
// #include "motor/StepperActuator.h"
