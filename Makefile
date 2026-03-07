# MARA Monorepo Makefile
# Unified build, test, and flash commands for all components

.PHONY: help install install-dev test test-host test-mcu test-hil test-hil-serial \
        build build-mcu build-cam flash flash-mcu flash-cam monitor-mcu monitor-cam \
        clean generate lint check-layers check-arch

# Python from virtual environment (create with: python3 -m venv .venv)
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

# HIL test defaults (override with: MCU_PORT=/dev/ttyUSB0 make test-hil)
MCU_PORT ?= /dev/cu.usbserial-0001
ROBOT_HOST ?= 10.0.0.60

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
	@echo "  test-hil       Run all HIL tests (TCP + serial, defaults: MCU_PORT=/dev/cu.usbserial-0001, ROBOT_HOST=10.0.0.60)"
	@echo "  test-hil-serial Run HIL tests via serial only"
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
	@echo "Architecture:"
	@echo "  check-arch     Run all architecture checks (host + firmware)"
	@echo "  check-layers   Check firmware layer dependencies"
	@echo ""
	@echo "Other:"
	@echo "  clean          Clean all build artifacts"
	@echo "  lint           Run linters"

# =============================================================================
# Installation
# =============================================================================

install:
	$(PIP) install -e host/

install-dev:
	$(PIP) install -e "host/[dev]"

# =============================================================================
# Testing
# =============================================================================

test: test-host test-mcu

test-host:
	cd host && ../$(PYTEST) tests/ -v

test-mcu:
	cd firmware/mcu && pio test -e native

# HIL tests (requires connected hardware)
# TCP: set ROBOT_HOST (default 10.0.0.60) and ROBOT_PORT (default 3333)
# Serial: set MCU_PORT (e.g., /dev/cu.usbserial-0001)
test-hil:
	cd host && MCU_PORT=$(MCU_PORT) ../$(PYTEST) tests/ -v --run-hil --mcu-port=$(MCU_PORT) --robot-host=$(ROBOT_HOST)

test-hil-serial:
	cd host && ../$(PYTEST) tests/ -v --run-hil --mcu-port=$(MCU_PORT)

test-hil-smoke:
	cd host && ../$(PYTEST) tests/test_hil_smoke.py -v --run-hil

test-hil-churn:
	cd host && ../$(PYTEST) tests/test_hil_churn.py -v --run-hil --churn-cycles=10

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
	cd host && ../$(PYTHON) -m mara_host.tools.generate_all

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
# Architecture Checks
# =============================================================================

check-arch: check-layers check-host-arch
	@echo "All architecture checks passed"

check-layers:
	cd firmware/mcu && python3 tools/check_layers.py

check-host-arch:
	cd host && ../$(PYTEST) tests/test_architecture.py -v

# =============================================================================
# Linting
# =============================================================================

lint:
	@echo "Linting not yet configured"
