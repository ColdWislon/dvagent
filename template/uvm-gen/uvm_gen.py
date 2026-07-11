#!/usr/bin/env python3
"""uvm-gen command-line entry point.

Usage: uvm_gen.py <config.yaml> [-o OUTPUT_DIR] [--force]
"""
from uvmgen.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
