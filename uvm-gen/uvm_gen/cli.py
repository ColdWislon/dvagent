"""Command line interface: uvm_gen.py <config.yaml> [-o OUTPUT_DIR] [--force]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, load_config
from .generator import (
    build_context,
    execute,
    finalize_context,
    new_agent_hints,
    plan,
)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="uvm_gen.py",
        description=(
            "Generate a complete SystemVerilog/UVM IP verification environment "
            "for Cadence Xcelium from a YAML configuration."
        ),
        epilog=(
            "Re-run policy: existing files are NEVER overwritten - re-running "
            "after adding agents/VIPs to the YAML creates only the new files. "
            "--force regenerates everything (except verif_matrix.yaml)."
        ),
    )
    p.add_argument("config", help="configuration YAML (may use 'extends: <base.yaml>')")
    p.add_argument(
        "-o",
        "--output-dir",
        default=".",
        help="directory in which <ip_name>_verif/ is created (default: .)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing generated files (verif_matrix.yaml is kept)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be created/skipped without writing anything",
    )
    p.add_argument("--version", action="version", version=f"uvm-gen {__version__}")
    return p


def main(argv=None) -> int:
    args = _parser().parse_args(argv)

    try:
        cfg, chain = load_config(args.config)
    except ConfigError as exc:
        print(f"uvm-gen: error: {exc}", file=sys.stderr)
        return 1

    for warning in cfg["warnings"]:
        print(f"uvm-gen: warning: {warning}", file=sys.stderr)

    ctx = build_context(cfg, input_basename=Path(args.config).name)
    env_root = Path(args.output_dir) / f"{cfg['ip_name']}_verif"
    finalize_context(ctx, Path(args.config), env_root)

    actions = plan(cfg, chain, ctx)
    result = execute(actions, env_root, ctx, force=args.force, dry_run=args.dry_run)

    mode = " (dry run - nothing written)" if args.dry_run else ""
    print(
        f"uvm-gen {__version__}: IP '{cfg['ip_name']}', configuration "
        f"'{cfg['config_name']}' (params hash {ctx['param_hash']}){mode}"
    )
    print(f"  environment root: {env_root}")
    for label, items in (
        ("created", result.created),
        ("overwritten", result.overwritten),
    ):
        print(f"  {label}: {len(items)} file(s)")
        for item in items:
            print(f"    + {item}" if label == "created" else f"    ~ {item}")
    if result.skipped:
        print(
            f"  skipped: {len(result.skipped)} file(s) already exist "
            "(uvm-gen never overwrites; use --force to regenerate)"
        )
    if result.protected:
        print(
            f"  kept: {', '.join(result.protected)} "
            "(verification history is never overwritten, even with --force)"
        )

    for hint in new_agent_hints(result, ctx):
        print(f"  NOTE: {hint}")

    if result.created and not result.skipped:
        ip = cfg["ip_name"]
        print("Next steps:")
        print(f"  cd {env_root}/sim")
        print("  make compile                     # elaboration sanity (stub DUT)")
        print(f"  make run TEST={ip}_smoke_test    # smoke test, UVM_ERROR count 0")
        print(f"  make run TEST={ip}_smoke_test PASSIVE=1   # SoC-reuse check")
    return 0
