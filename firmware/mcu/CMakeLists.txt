# firmware/mcu/CMakeLists.txt
# =============================================================================
# MARA Runtime - CMake Build Configuration for Linux
# =============================================================================
#
# Build MARA firmware as a shared library for Linux robots
# (Raspberry Pi, Jetson, etc.)
#
# Usage:
#   mkdir build && cd build
#   cmake .. -DPLATFORM_LINUX=ON
#   make -j$(nproc)
#
# Output:
#   libmara_runtime.so  - Core firmware library
#   libmara_capi.so     - C API wrapper for Python bindings
#
# =============================================================================

cmake_minimum_required(VERSION 3.16)
project(mara_runtime VERSION 1.0.0 LANGUAGES CXX)

# =============================================================================
# Build Configuration
# =============================================================================

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Build type defaults to Release
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Platform selection
option(PLATFORM_LINUX "Build for Linux (Raspberry Pi, Jetson, etc.)" ON)
option(PLATFORM_NATIVE "Build for native/test" OFF)

# Feature flags (from mara_build.yaml)
option(HAS_WIFI "Enable WiFi support" OFF)
option(HAS_BLE "Enable BLE support" OFF)
option(HAS_SERVO "Enable servo support" ON)
option(HAS_DC_MOTOR "Enable DC motor support" ON)
option(HAS_STEPPER "Enable stepper motor support" ON)
option(HAS_ENCODER "Enable encoder support" ON)
option(HAS_IMU "Enable IMU support" ON)
option(HAS_ULTRASONIC "Enable ultrasonic sensor support" ON)
option(HAS_SIGNAL_BUS "Enable signal bus" ON)
option(HAS_CONTROL_KERNEL "Enable control kernel" ON)
option(HAS_PID_CONTROLLER "Enable PID controller" ON)
option(HAS_STATE_SPACE "Enable state-space controller" ON)
option(HAS_OBSERVER "Enable observer" ON)
option(HAS_CONTROL_MODULE "Enable control module" ON)
option(HAS_TELEMETRY "Enable telemetry" ON)
option(HAS_LOGGING "Enable logging" ON)
option(HAS_IDENTITY "Enable identity module" ON)
option(HAS_MQTT_TRANSPORT "Enable MQTT transport (requires HAS_WIFI)" OFF)
option(HAS_OTA "Enable OTA updates (requires HAS_WIFI)" OFF)

# =============================================================================
# Compiler Definitions
# =============================================================================

# Platform defines
if(PLATFORM_LINUX)
    add_definitions(
        -DPLATFORM_LINUX=1
        -DPLATFORM_ESP32=0
        -DPLATFORM_STM32=0
        -DPLATFORM_RP2040=0
        -DPLATFORM_NATIVE=0
    )
elseif(PLATFORM_NATIVE)
    add_definitions(
        -DPLATFORM_LINUX=0
        -DPLATFORM_ESP32=0
        -DPLATFORM_STM32=0
        -DPLATFORM_RP2040=0
        -DPLATFORM_NATIVE=1
    )
endif()

# Feature defines
if(HAS_WIFI)
    add_definitions(-DHAS_WIFI=1)
else()
    add_definitions(-DHAS_WIFI=0)
endif()

if(HAS_BLE)
    add_definitions(-DHAS_BLE=1)
else()
    add_definitions(-DHAS_BLE=0)
endif()

if(HAS_SERVO)
    add_definitions(-DHAS_SERVO=1)
else()
    add_definitions(-DHAS_SERVO=0)
endif()

if(HAS_DC_MOTOR)
    add_definitions(-DHAS_DC_MOTOR=1)
else()
    add_definitions(-DHAS_DC_MOTOR=0)
endif()

if(HAS_STEPPER)
    add_definitions(-DHAS_STEPPER=1)
else()
    add_definitions(-DHAS_STEPPER=0)
endif()

if(HAS_ENCODER)
    add_definitions(-DHAS_ENCODER=1)
else()
    add_definitions(-DHAS_ENCODER=0)
endif()

if(HAS_IMU)
    add_definitions(-DHAS_IMU=1)
else()
    add_definitions(-DHAS_IMU=0)
endif()

if(HAS_ULTRASONIC)
    add_definitions(-DHAS_ULTRASONIC=1)
else()
    add_definitions(-DHAS_ULTRASONIC=0)
endif()

if(HAS_SIGNAL_BUS)
    add_definitions(-DHAS_SIGNAL_BUS=1)
else()
    add_definitions(-DHAS_SIGNAL_BUS=0)
endif()

if(HAS_CONTROL_KERNEL)
    add_definitions(-DHAS_CONTROL_KERNEL=1)
else()
    add_definitions(-DHAS_CONTROL_KERNEL=0)
endif()

if(HAS_PID_CONTROLLER)
    add_definitions(-DHAS_PID_CONTROLLER=1)
else()
    add_definitions(-DHAS_PID_CONTROLLER=0)
endif()

if(HAS_STATE_SPACE)
    add_definitions(-DHAS_STATE_SPACE=1)
else()
    add_definitions(-DHAS_STATE_SPACE=0)
endif()

if(HAS_OBSERVER)
    add_definitions(-DHAS_OBSERVER=1)
else()
    add_definitions(-DHAS_OBSERVER=0)
endif()

if(HAS_CONTROL_MODULE)
    add_definitions(-DHAS_CONTROL_MODULE=1)
else()
    add_definitions(-DHAS_CONTROL_MODULE=0)
endif()

if(HAS_TELEMETRY)
    add_definitions(-DHAS_TELEMETRY=1)
else()
    add_definitions(-DHAS_TELEMETRY=0)
endif()

if(HAS_LOGGING)
    add_definitions(-DHAS_LOGGING=1)
else()
    add_definitions(-DHAS_LOGGING=0)
endif()

if(HAS_IDENTITY)
    add_definitions(-DHAS_IDENTITY=1)
else()
    add_definitions(-DHAS_IDENTITY=0)
endif()

if(HAS_MQTT_TRANSPORT)
    add_definitions(-DHAS_MQTT_TRANSPORT=1)
else()
    add_definitions(-DHAS_MQTT_TRANSPORT=0)
endif()

if(HAS_OTA)
    add_definitions(-DHAS_OTA=1)
else()
    add_definitions(-DHAS_OTA=0)
endif()

# =============================================================================
# Include Directories
# =============================================================================

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/test/fakes
    ${CMAKE_CURRENT_SOURCE_DIR}/.pio/libdeps/native/ArduinoJson/src
)

# =============================================================================
# Source Files
# =============================================================================

# All firmware sources except the Arduino entry point (main.cpp)
file(GLOB_RECURSE ALL_SOURCES src/*.cpp)
list(FILTER ALL_SOURCES EXCLUDE REGEX ".*/src/main\\.cpp$")

# Split into platform-specific and core groups for clarity
# (combined into mara_runtime below)
set(CORE_SOURCES "")
set(LINUX_HAL_SOURCES "")
set(HAL_DRIVER_SOURCES "")
foreach(src ${ALL_SOURCES})
    if(src MATCHES ".*/hal/linux/.*")
        list(APPEND LINUX_HAL_SOURCES ${src})
    elseif(src MATCHES ".*/hal/drivers/.*")
        list(APPEND HAL_DRIVER_SOURCES ${src})
    elseif(NOT src MATCHES ".*/hal/esp32/.*")
        list(APPEND CORE_SOURCES ${src})
    endif()
endforeach()

# C API wrapper
set(CAPI_SOURCES
    src/api/mara_capi.cpp
)

# =============================================================================
# Dependencies
# =============================================================================

find_package(PkgConfig REQUIRED)
find_package(Threads REQUIRED)

# libgpiod for GPIO access
pkg_check_modules(GPIOD libgpiod)
if(GPIOD_FOUND)
    message(STATUS "Found libgpiod: ${GPIOD_VERSION}")
    add_definitions(-DHAS_LIBGPIOD=1)
else()
    message(WARNING "libgpiod not found - GPIO support disabled")
    add_definitions(-DHAS_LIBGPIOD=0)
endif()

# =============================================================================
# Libraries
# =============================================================================

# Main runtime library
add_library(mara_runtime SHARED
    ${CORE_SOURCES}
    ${LINUX_HAL_SOURCES}
    ${HAL_DRIVER_SOURCES}
)

target_include_directories(mara_runtime PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(mara_runtime PRIVATE
    Threads::Threads
    rt  # For clock_gettime, timerfd
)

if(GPIOD_FOUND)
    target_link_libraries(mara_runtime PRIVATE ${GPIOD_LIBRARIES})
    target_include_directories(mara_runtime PRIVATE ${GPIOD_INCLUDE_DIRS})
endif()

# Set library version
set_target_properties(mara_runtime PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
)

# C API wrapper library
add_library(mara_capi SHARED
    ${CAPI_SOURCES}
)

target_link_libraries(mara_capi PRIVATE
    mara_runtime
)

set_target_properties(mara_capi PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
)

# =============================================================================
# Installation
# =============================================================================

install(TARGETS mara_runtime mara_capi
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/
    DESTINATION include
    FILES_MATCHING PATTERN "*.h"
)

# Install API header separately for easy access
install(FILES include/api/mara_capi.h
    DESTINATION include/mara
)

# =============================================================================
# Package Configuration
# =============================================================================

# Generate pkg-config file
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/mara_runtime.pc.in
    ${CMAKE_CURRENT_BINARY_DIR}/mara_runtime.pc
    @ONLY
)

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/mara_runtime.pc
    DESTINATION lib/pkgconfig
)

# =============================================================================
# Summary
# =============================================================================

message(STATUS "")
message(STATUS "MARA Runtime Configuration:")
message(STATUS "  Platform:        ${CMAKE_SYSTEM_NAME}")
message(STATUS "  Build type:      ${CMAKE_BUILD_TYPE}")
message(STATUS "  C++ Standard:    ${CMAKE_CXX_STANDARD}")
message(STATUS "  Install prefix:  ${CMAKE_INSTALL_PREFIX}")
message(STATUS "")
message(STATUS "Features:")
message(STATUS "  WiFi:            ${HAS_WIFI}")
message(STATUS "  BLE:             ${HAS_BLE}")
message(STATUS "  Servo:           ${HAS_SERVO}")
message(STATUS "  DC Motor:        ${HAS_DC_MOTOR}")
message(STATUS "  Stepper:         ${HAS_STEPPER}")
message(STATUS "  Encoder:         ${HAS_ENCODER}")
message(STATUS "  IMU:             ${HAS_IMU}")
message(STATUS "  Signal Bus:      ${HAS_SIGNAL_BUS}")
message(STATUS "  Control Kernel:  ${HAS_CONTROL_KERNEL}")
message(STATUS "")
