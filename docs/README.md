# MARA Documentation

**Modular Asynchronous Robotics Architecture**
```
 ███╗   ███╗ █████╗ ██████╗  █████╗
 ████╗ ████║██╔══██╗██╔══██╗██╔══██╗
 ██╔████╔██║███████║██████╔╝███████║
 ██║╚██╔╝██║██╔══██║██╔══██╗██╔══██║
 ██║ ╚═╝ ██║██║  ██║██║  ██║██║  ██║
 ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
 Modular Asynchronous Robotics Architecture
```

---

## Quick Links

| Getting Started | I want to... |
|-----------------|--------------|
| [Getting Started](GETTING_STARTED.md) | Set up hardware and run first example |
| [Architecture Overview](ARCHITECTURE.md) | Understand system design |

---

## Documentation Index

### Architecture

Core system design and constraints.

| Document | Description |
|----------|-------------|
| [Architecture Overview](ARCHITECTURE.md) | Main system diagram and component overview |
| [System Flow](architecture/SYSTEM_FLOW.md) | Complete layer-by-layer data flow |
| [Host Layers](architecture/HOST_LAYERS.md) | Python host 4-layer architecture |
| [Layer Boundaries](architecture/LAYER_BOUNDARIES.md) | Inter-layer contracts and dependencies |
| [Composition](architecture/COMPOSITION.md) | Robot vs Runtime vs Services patterns |
| [Architecture Rules](architecture/RULES.md) | Design constraints and coupling rules |

### Extension Guides

How to add new functionality.

| Document | Description |
|----------|-------------|
| [Robot Abstraction Layer](guides/ROBOT_LAYER.md) | Semantic robot control for LLM integration |
| [MCP & HTTP Server](guides/MCP_HTTP.md) | LLM interface (Claude, OpenAI, any LLM) |
| [Adding Commands](guides/ADDING_COMMANDS.md) | Add new protocol commands |
| [Adding Control Blocks](guides/ADDING_CONTROL.md) | Add controllers, observers, filters |
| [Adding Hardware](guides/ADDING_HARDWARE.md) | Add sensors, actuators, peripherals |
| [Extending MARA](guides/EXTENDING.md) | Transports, sensors, motors, services |
| [Extensibility Patterns](guides/EXTENSIBILITY.md) | Quick reference for one-file patterns |

### Reference

Technical specifications.

| Document | Description |
|----------|-------------|
| [Code Generation](reference/CODEGEN.md) | Build system and code generators |
| [MQTT Fleet Control](reference/MQTT.md) | Multi-robot networking |
| [Monorepo Layout](reference/MONOREPO.md) | Repository structure and boundaries |

### Diagrams

Visual documentation (Mermaid sources + rendered).

| Diagram | Description |
|---------|-------------|
| [mara_overview](diagrams/mara_overview.svg) | High-level system overview |
| [dataflow](diagrams/dataflow.svg) | Data flow through layers |
| [codegen](diagrams/codegen.svg) | Code generation pipeline |
| [end_to_end_flow](diagrams/end_to_end_flow.svg) | Complete request lifecycle |

---

## Module Documentation

In-place documentation for specific modules.

| Module | Location | Description |
|--------|----------|-------------|
| API Reference | [host/mara_host/api/README.md](../host/mara_host/api/README.md) | Public API (GPIO, PWM, Servo, Motor) |
| Camera | [host/mara_host/camera/README.md](../host/mara_host/camera/README.md) | ESP32-CAM integration |
| Research Toolkit | [host/mara_host/research/README.md](../host/mara_host/research/README.md) | Simulation, sysid, analysis |
| Examples | [host/examples/README.md](../host/examples/README.md) | Usage examples |
| MCU Firmware | [firmware/mcu/README.md](../firmware/mcu/README.md) | C++ firmware |

---

## Navigation

```
docs/
├── README.md              ← You are here
├── GETTING_STARTED.md     ← Start here
├── ARCHITECTURE.md        ← System overview
├── architecture/          ← Deep dives
│   ├── SYSTEM_FLOW.md
│   ├── HOST_LAYERS.md
│   ├── LAYER_BOUNDARIES.md
│   ├── COMPOSITION.md
│   └── RULES.md
├── guides/                ← How-to guides
│   ├── ROBOT_LAYER.md
│   ├── MCP_HTTP.md
│   ├── ADDING_COMMANDS.md
│   ├── ADDING_CONTROL.md
│   ├── ADDING_HARDWARE.md
│   ├── EXTENDING.md
│   └── EXTENSIBILITY.md
├── reference/             ← Technical specs
│   ├── CODEGEN.md
│   ├── MQTT.md
│   └── MONOREPO.md
└── diagrams/              ← Visual docs
    ├── *.mmd              (Mermaid sources)
    ├── *.svg              (Vector renders)
    └── *.png              (Raster renders)
```
