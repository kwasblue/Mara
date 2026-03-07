#pragma once

#include <cstdint>

namespace mara {

struct ServiceContext;

/// Run the control loop (DC motor PID, motion controller update).
/// @param ctx Service context
/// @param now_ms Current time in milliseconds
/// @param dt Time since last call in seconds
void runControlLoop(ServiceContext& ctx, uint32_t now_ms, float dt);

/// Run the safety loop (ModeManager update).
/// @param ctx Service context
/// @param now_ms Current time in milliseconds
void runSafetyLoop(ServiceContext& ctx, uint32_t now_ms);

} // namespace mara
