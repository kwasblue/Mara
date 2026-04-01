# services/tooling/backends/implementations/__init__.py
"""Backend implementations for build, flash, and test operations.

Each subdirectory implements the interfaces defined in backends/interfaces.py:
- platformio/  - PlatformIO toolchain (default)
- cmake/       - CMake/ESP-IDF toolchain

To add a new backend, create a new directory here with:
1. build_backend.py  - implements BuildBackend
2. flash_backend.py  - implements FlashBackend
3. test_backend.py   - implements TestBackend
4. __init__.py       - exports register_backends() function

Then run: mara generate tooling
"""

# Implementations are loaded dynamically by registry.py via _generated_loaders.py
