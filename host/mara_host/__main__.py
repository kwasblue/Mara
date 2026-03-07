#!/usr/bin/env python3
# mara_host/__main__.py
"""Enable running mara_host as a module: python -m mara_host"""

import sys

from mara_host.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
