#!/usr/bin/env python3
"""uvm-gen entry point: uvm_gen.py <config.yaml> [-o OUTPUT_DIR] [--force]"""

import sys

from uvm_gen.cli import main

if __name__ == "__main__":
    sys.exit(main())
