"""Command-line interface: uvm_gen.py <config.yaml> [-o OUTPUT_DIR] [--force]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, load_config, validate
from .generate import generate


def _parser():
    parser = argparse.ArgumentParser(
        prog="uvm_gen.py",
        description=(
            "Generate a complete SystemVerilog/UVM IP verification environment "
            "for Cadence Xcelium from a YAML configuration."),
    )
    parser.add_argument("config", help="IP configuration YAML (supports 'extends')")
    parser.add_argument(
        "-o", "--output-dir", default=".",
        help="directory in which <ip_name>_verif/ is created (default: .)")
    parser.add_argument(
        "--force", action="store_true",
        help="overwrite ALL existing files (default: never overwrite — only "
             "files that don't exist yet are created)")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="report what would be created/kept without writing anything")
    parser.add_argument(
        "--version", action="version", version=f"uvm-gen {__version__}")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)

    try:
        merged, chain = load_config(args.config)
        cfg = validate(merged)
        report = generate(cfg, chain, Path(args.output_dir),
                          force=args.force, dry_run=args.dry_run)
    except ConfigError as exc:
        print(f"uvm-gen: error: {exc}", file=sys.stderr)
        return 2

    mode = "DRY RUN — nothing written" if args.dry_run else "generated"
    print(f"uvm-gen {__version__}: {cfg['ip_name']} "
          f"(config '{cfg['config_name']}') — {mode}")
    print(f"  environment root: {report.env_root}")

    if report.created:
        print(f"\n  new files ({len(report.created)}):")
        for rel in report.created:
            print(f"    [new]    {rel}")
    if report.forced:
        print(f"\n  overwritten with --force ({len(report.forced)}):")
        for rel in report.forced:
            print(f"    [force]  {rel}")
    if report.skipped:
        print(f"\n  existing files kept untouched: {len(report.skipped)}")

    if report.stale:
        print(f"\n  NOTE: {len(report.stale)} existing file(s) differ from what this "
              "config would generate (kept as-is):")
        for rel in report.stale:
            print(f"    [stale]  {rel}")
        print("  After adding agents/VIPs, wire them into these files by hand "
              "(see README) or re-run with --force to regenerate EVERYTHING "
              "(this destroys local edits).")

    if not report.created and not report.forced:
        print("\n  nothing to do — all files already exist "
              "(use --force to regenerate).")
    elif report.created and not args.dry_run:
        env_dir = report.env_root
        print("\n  next steps:")
        print(f"    cd {env_dir}/sim")
        print("    make compile                       # elaboration sanity")
        print(f"    make run TEST={cfg['ip_name']}_smoke_test")
    return 0
