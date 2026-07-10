"""Command line interface: uvm_gen.py <config.yaml> [-o OUTPUT_DIR] [--force]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, load_config
from .copilot import find_pack, plan_copilot
from .generator import (
    build_context,
    check_collisions,
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
    p.add_argument(
        "--copilot-pack",
        metavar="PATH",
        help=(
            "root of the GitHub Copilot DV agent pack to stage into the env "
            "(the directory containing .github/). Default: auto-discovered "
            "next to uvm-gen; YAML key 'copilot:' also accepts a path"
        ),
    )
    p.add_argument(
        "--no-copilot",
        action="store_true",
        help="do not stage the Copilot DV agent pack into the environment",
    )
    p.add_argument("--version", action="version", version=f"uvm-gen {__version__}")
    return p


def _resolve_copilot(args, cfg) -> "Path | None":
    """Returns the pack root to stage, or None. Precedence:
    --no-copilot > --copilot-pack > YAML copilot: false/path/true > auto."""
    if args.no_copilot:
        return None
    config_dir = Path(args.config).resolve().parent
    if args.copilot_pack:
        return find_pack(args.copilot_pack, config_dir=config_dir)
    yaml_copilot = cfg["copilot"]
    if yaml_copilot is False:
        return None
    if isinstance(yaml_copilot, str):
        return find_pack(yaml_copilot, config_dir=config_dir)
    pack = find_pack()
    if pack is None and yaml_copilot is True:
        raise ConfigError(
            "the configuration requests the Copilot DV agent pack "
            "(copilot: true) but none was found next to uvm-gen - point "
            "--copilot-pack (or 'copilot: <path>') at a pack root"
        )
    return pack


def main(argv=None) -> int:
    args = _parser().parse_args(argv)

    try:
        cfg, chain = load_config(args.config)
    except ConfigError as exc:
        print(f"uvm-gen: error: {exc}", file=sys.stderr)
        return 1

    for warning in cfg["warnings"]:
        print(f"uvm-gen: warning: {warning}", file=sys.stderr)

    try:
        pack_root = _resolve_copilot(args, cfg)
    except ConfigError as exc:
        print(f"uvm-gen: error: {exc}", file=sys.stderr)
        return 1

    ctx = build_context(cfg, input_basename=Path(args.config).name)
    ctx["has_copilot"] = pack_root is not None
    env_root = Path(args.output_dir) / f"{cfg['ip_name']}_verif"
    finalize_context(ctx, Path(args.config), env_root)

    actions = plan(cfg, chain, ctx)
    if pack_root is not None:
        actions += plan_copilot(pack_root)
    check_collisions(actions)
    result = execute(actions, env_root, ctx, force=args.force, dry_run=args.dry_run)

    mode = " (dry run - nothing written)" if args.dry_run else ""
    print(
        f"uvm-gen {__version__}: IP '{cfg['ip_name']}', configuration "
        f"'{cfg['config_name']}' (params hash {ctx['param_hash']}){mode}"
    )
    print(f"  environment root: {env_root}")
    if pack_root is not None:
        print(f"  copilot pack: staged from {pack_root} (see GETTING_STARTED.md)")
    else:
        print(
            "  copilot pack: not staged"
            + (
                ""
                if args.no_copilot or cfg["copilot"] is False
                else " (none found next to uvm-gen; use --copilot-pack PATH)"
            )
        )
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
