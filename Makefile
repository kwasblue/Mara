# MARA Monorepo Makefile
# Unified build, test, and flash commands for all components

.PHONY: help install install-dev test test-host test-mcu build build-mcu build-cam \
        flash flash-mcu flash-cam monitor-mcu monitor-cam clean generate lint

# Default target
help:
	@echo "MARA - Modular Asynchronous Robotics Architecture"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Installation:"
	@echo "  install        Install host package in development mode"
	@echo "  install-dev    Install with development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test           Run all tests (host + firmware)"
	@echo "  test-host      Run Python host tests"
	@echo "  test-mcu       Run MCU firmware tests (native)"
	@echo ""
	@echo "Building:"
	@echo "  build          Build all firmware"
	@echo "  build-mcu      Build MCU firmware (default env)"
	@echo "  build-mcu-ENV  Build MCU firmware (specific env: minimal, motors, control, full)"
	@echo "  build-cam      Build CAM firmware"
	@echo ""
	@echo "Flashing:"
	@echo "  flash-mcu      Flash MCU firmware"
	@echo "  flash-cam      Flash CAM firmware"
	@echo ""
	@echo "Monitoring:"
	@echo "  monitor-mcu    Open MCU serial monitor"
	@echo "  monitor-cam    Open CAM serial monitor"
	@echo ""
	@echo "Code Generation:"
	@echo "  generate       Run all code generators"
	@echo ""
	@echo "Other:"
	@echo "  clean          Clean all build artifacts"
	@echo "  lint           Run linters"

# =============================================================================
# Installation
# =============================================================================

install:
	cd host && pip install -e .

install-dev:
	cd host && pip install -e ".[dev]"

# =============================================================================
# Testing
# =============================================================================

test: test-host test-mcu

test-host:
	cd host && pytest tests/ -v

test-mcu:
	cd firmware/mcu && pio test -e native

# =============================================================================
# Building
# =============================================================================

build: build-mcu build-cam

build-mcu:
	cd firmware/mcu && pio run

build-mcu-minimal:
	cd firmware/mcu && pio run -e esp32_minimal

build-mcu-motors:
	cd firmware/mcu && pio run -e esp32_motors

build-mcu-control:
	cd firmware/mcu && pio run -e esp32_control

build-mcu-full:
	cd firmware/mcu && pio run -e esp32_full

build-cam:
	cd firmware/cam && pio run

# =============================================================================
# Flashing
# =============================================================================

flash-mcu:
	cd firmware/mcu && pio run -t upload

flash-cam:
	cd firmware/cam && pio run -t upload

# =============================================================================
# Monitoring
# =============================================================================

monitor-mcu:
	cd firmware/mcu && pio device monitor

monitor-cam:
	cd firmware/cam && pio device monitor

# =============================================================================
# Code Generation
# =============================================================================

generate:
	cd host && python -m mara_host.tools.generate_all

# =============================================================================
# Cleanup
# =============================================================================

clean:
	cd firmware/mcu && pio run -t clean
	cd firmware/cam && pio run -t clean
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# =============================================================================
# Linting
# =============================================================================

lint:
	@echo "Linting not yet configured"
