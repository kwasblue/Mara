#!/usr/bin/env python3
# robot_host/__main__.py
"""Enable running robot_host as a module: python -m robot_host"""

import sys

from robot_host.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
